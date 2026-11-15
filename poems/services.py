from django.db.models import Q

def filter_poems(queryset, data):
    for field, relation in [('language', 'language'), ('class_level', 'classes'), ('category', 'categories')]:
        if data.get(field):
            queryset = queryset.filter(**{relation: data[field]})
    if data.get('country'): queryset = queryset.filter(source_work__country=data['country'])
    if data.get('age'): queryset = queryset.filter(age_min__lte=data['age'], age_max__gte=data['age'])
    if data.get('collection') == 'verified': queryset = queryset.filter(source_verified=True)
    if data.get('collection') == 'original': queryset = queryset.filter(content_kind__in=['original','ai_demo'])
    for term in data.get('q', '').split():
        queryset = queryset.filter(
            Q(title__icontains=term) | Q(keywords__icontains=term) | Q(author__icontains=term)
            | Q(poem_text__icontains=term) | Q(language__name__icontains=term)
            | Q(language__native_name__icontains=term) | Q(categories__name__icontains=term)
            | Q(classes__name__icontains=term)
        )
    ordering = {'title': ('title', 'id'), 'oldest': ('published_at', 'id'), 'featured': ('-is_featured', '-published_at', '-id')}
    return queryset.distinct().order_by(*ordering.get(data.get('sort'), ('-published_at', '-id')))
