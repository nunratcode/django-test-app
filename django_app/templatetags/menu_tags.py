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
    
    request = context.get('request', None)

    items_qs = MenuItem.objects.filter(menu__name=menu_name).select_related('parent').order_by('order', 'id')
    items = list(items_qs) 

    if not items:
        return ''

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

    for parent_id, child_ids in children_map.items():
        if parent_id is None:
            continue
        if parent_id in nodes:
            nodes[parent_id]['children'].extend(child_ids)

    active_ids = set()
    if request is not None:
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
            if it.named_url and current_view_name:
                try:
                    item_args = it.named_args or []
                    item_kwargs = it.named_kwargs or {}
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
                    if it.named_url == current_view_name:
                        ok_args = (not item_args) or tuple(item_args) == current_args
                        ok_kwargs = (not item_kwargs) or all(k in current_kwargs and current_kwargs[k] == v for k, v in item_kwargs.items())
                        if ok_args and ok_kwargs:
                            node['active'] = True
                            active_ids.add(nid)
                            continue
                except Exception:
                    pass
            ru = node.get('resolved_url')
            if ru:
                try:
                    if ru == current_path or ru.rstrip('/') == current_path.rstrip('/'):
                        node['active'] = True
                        active_ids.add(nid)
                        continue
                except Exception:
                    pass

    parent_map = {it.id: it.parent_id for it in items}
    def mark_ancestors(nid):
        pid = parent_map.get(nid)
        if not pid:
            return
        if pid in nodes:
            nodes[pid]['expanded'] = True
            mark_ancestors(pid)

    for aid in list(active_ids):
        nodes[aid]['expanded'] = True
        mark_ancestors(aid)
        for child_id in nodes[aid]['children']:
            nodes[child_id]['expanded'] = True

    def build_subtree(parent_id):
        subtree = []
        for cid in children_map.get(parent_id, []):
            node = nodes[cid]
            children = build_subtree(node['item'].id)
            if any(child['expanded'] or child['active'] for child in children):
             node['expanded'] = True

            subtree.append({
                'item': node['item'],
                'children': children,
                'expanded': node['expanded'],
                'active': node['active'],
                'url': node['resolved_url'],
            })
        return subtree

    tree = build_subtree(None)

    render_context = {
        'menu_name': menu_name,
        'tree': tree,
        'request': request,
    }

    ctx = context.flatten()
    ctx.update(render_context)
    html = render_to_string(template_name, ctx)
    return mark_safe(html)