from django.db import migrations


def bump_6_to_15(apps, schema_editor):
    """기존 환자의 종결 목표를 구 기본값(6) → 관리급여 한도(15)로 갱신."""
    Patient = apps.get_model('scheduler', 'Patient')
    Patient.objects.filter(target_sessions=6).update(target_sessions=15)


def revert_15_to_6(apps, schema_editor):
    Patient = apps.get_model('scheduler', 'Patient')
    Patient.objects.filter(target_sessions=15).update(target_sessions=6)


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0005_patient_external_sessions_and_more'),
    ]

    operations = [
        migrations.RunPython(bump_6_to_15, revert_15_to_6),
    ]
