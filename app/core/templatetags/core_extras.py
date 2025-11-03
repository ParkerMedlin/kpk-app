from django import template
from django.contrib.auth.models import Group
from django.template import loader, TemplateDoesNotExist
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="has_group")
def has_group(user, group_name):
    group = Group.objects.get(name=group_name)
    return True if group in user.groups.all() else False


@register.simple_tag(takes_context=True)
def include_optional(context, template_name):
    """
    Render ``template_name`` if it exists, otherwise return an empty string.

    This lets developers drop local-only templates (e.g. gitignored files)
    without breaking the shared template when the file is absent.
    """
    if not template_name:
        return ""
    try:
        template_obj = loader.get_template(template_name)
    except TemplateDoesNotExist:
        return ""

    # Re-render using the current context so the optional template can
    # access the same variables as the calling template.
    rendered = template_obj.render(context.flatten(), request=context.get("request"))
    return mark_safe(rendered)
