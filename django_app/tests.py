from django.test import TestCase, RequestFactory
from django.template import Context, Template
from django_app.models import Menu, MenuItem

class MenuTemplateTagTests(TestCase):
    def setUp(self):
        self.menu = Menu.objects.create(name='main_menu', title='Главное меню')
        self.root1 = MenuItem.objects.create(menu=self.menu, title='Главная', external_url='/')
        self.root2 = MenuItem.objects.create(menu=self.menu, title='О компании', external_url='/about/')
        self.child = MenuItem.objects.create(menu=self.menu, title='Команда', parent=self.root2, external_url='/about/team/')

        self.factory = RequestFactory()

    def render_menu(self, path='/'):
        request = self.factory.get(path)
        context = Context({'request': request})
        template = Template("{% load menu_tags %}{% draw_menu 'main_menu' %}")
        return template.render(context)

    def test_menu_renders_without_errors(self):
        html = self.render_menu('/')
        self.assertIn('Главная', html)
        self.assertIn('О компании', html)

    def test_active_item_detected_by_url(self):
        html = self.render_menu('/about/')
        self.assertIn('active', html)

    def test_one_database_query(self):
        with self.assertNumQueries(1):
            self.render_menu('/')

    def test_child_menu_expanded_when_active(self):
        html = self.render_menu('/about/team/')
        self.assertIn('Команда', html)
        self.assertIn('О компании', html)