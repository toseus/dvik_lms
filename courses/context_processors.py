def program_filters(request):
    if request.user.is_authenticated:
        from .models import TrainingProgram, Department
        qs = TrainingProgram.objects.filter(status='В работе')
        categories = qs.values_list('category', flat=True).distinct().order_by('category')
        departments_list = Department.objects.filter(is_active=True)
        return {
            'program_categories': [c for c in categories if c],
            'departments_list': departments_list,
        }
    return {}


def student_filters(request):
    if request.user.is_authenticated:
        from .models import Person
        positions = (
            Person.objects
            .filter(user__isnull=False, position__gt='')
            .values_list('position', flat=True)
            .distinct()
            .order_by('position')[:100]
        )
        return {'student_positions': list(positions)}
    return {}
