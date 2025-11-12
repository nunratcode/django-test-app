# Template tag для отрисовки меню: {% draw_menu 'main_menu' %}
from django import template
from django.template.loader import render_to_string
from django.urls import resolve
from django.utils.safestring import mark_safe
from django_app.models import Menu, MenuItem
import collections
import json

register = template.Library()

@register.simple_tag(takes_context=True)
def draw_menu(context, menu_name, template_name="django_app/menu.html"):
    """
    Рендерит дерево меню по имени menu_name.
    Важно: делает ровно 1 запрос к базе — выбирает все пункты меню и далее работает в памяти.
    """
    request = context.get('request', None)

    # Выполняем один запрос: все пункты меню с parent (select_related для parent)
    # Превращаем в список (оценка queryset) — один запрос к БД.
    items_qs = MenuItem.objects.filter(menu__name=menu_name).select_related('parent').order_by('order', 'id')
    items = list(items_qs)  # именно тут выполняется SQL-запрос

    if not items:
        return ''

    # Собираем узлы и карту детей
    nodes = {}
    children_map = collections.defaultdict(list)
    for it in items:
        nodes[it.id] = {
            'item': it,
            'children': [],
            'expanded': False,
            'active': False,
            'resolved_url': it.get_resolved_url(),
        }
        children_map[it.parent_id].append(it.id)

    # Присоединяем списки children к родителям в nodes
    for parent_id, child_ids in children_map.items():
        if parent_id is None:
            continue
        if parent_id in nodes:
            nodes[parent_id]['children'].extend(child_ids)

    # Определяем активные пункты (сравнение по named_url и/или по пути)
    active_ids = set()
    if request is not None:
        # Получим информацию о текущем view (если доступна)
        try:
            resolver_match = request.resolver_match
        except Exception:
            resolver_match = None

        current_view_name = resolver_match.view_name if resolver_match else None
        current_args = tuple(resolver_match.args) if resolver_match else ()
        current_kwargs = resolver_match.kwargs if resolver_match else {}
        current_path = request.path

        for nid, node in nodes.items():
            it = node['item']
            # 1) сравнение по named_url (если задано)
            if it.named_url and current_view_name:
                try:
                    item_args = it.named_args or []
                    item_kwargs = it.named_kwargs or {}
                    # если хранилось как строка, попытаемся распарсить
                    if isinstance(item_args, str):
                        try:
                            item_args = json.loads(item_args)
                        except Exception:
                            item_args = []
                    if isinstance(item_kwargs, str):
                        try:
                            item_kwargs = json.loads(item_kwargs)
                        except Exception:
                            item_kwargs = {}
                    # сравнение view name и (при наличии у пункта) args/kwargs
                    if it.named_url == current_view_name:
                        ok_args = (not item_args) or tuple(item_args) == current_args
                        ok_kwargs = (not item_kwargs) or all(k in current_kwargs and current_kwargs[k] == v for k, v in item_kwargs.items())
                        if ok_args and ok_kwargs:
                            node['active'] = True
                            active_ids.add(nid)
                            continue
                except Exception:
                    pass
            # 2) сравнение по resolved_url (если удалось разрешить) и текущему path
            ru = node.get('resolved_url')
            if ru:
                try:
                    # простое сравнение пути; учитываем trailing slash
                    if ru == current_path or ru.rstrip('/') == current_path.rstrip('/'):
                        node['active'] = True
                        active_ids.add(nid)
                        continue
                except Exception:
                    pass

    # Функция для пометки предков как expanded
    parent_map = {it.id: it.parent_id for it in items}
    def mark_ancestors(nid):
        pid = parent_map.get(nid)
        if not pid:
            return
        if pid in nodes:
            nodes[pid]['expanded'] = True
            mark_ancestors(pid)

    # Проставляем expanded для активных и их предков,
    # также расширяем первый уровень под активным пунктом
    for aid in list(active_ids):
        nodes[aid]['expanded'] = True
        mark_ancestors(aid)
        # первый уровень детей активного пункта раскрыт
        for child_id in nodes[aid]['children']:
            nodes[child_id]['expanded'] = True

    # Рекурсивно строим древовидную структуру для шаблона
    def build_subtree(parent_id):
        subtree = []
        for cid in children_map.get(parent_id, []):
            node = nodes[cid]
            subtree.append({
                'item': node['item'],
                'children': build_subtree(node['item'].id),
                'expanded': node['expanded'],
                'active': node['active'],
                'url': node['resolved_url'],
            })
        return subtree

    tree = build_subtree(None)

    # Готовим контекст для рендера шаблона
    render_context = {
        'menu_name': menu_name,
        'tree': tree,
        'request': request,
    }

    # Включаем текущий контекст шаблона (чтобы доступ к переменным сохранился)
    ctx = context.flatten()
    ctx.update(render_context)
    html = render_to_string(template_name, ctx)
    return mark_safe(html)