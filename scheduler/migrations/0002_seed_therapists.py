from django.db import migrations


# 엑셀 '근골격계도수치료 처방 명단'의 담당치료사
SEED = ['최수홍', '김대현', '김예지']


def seed_therapists(apps, schema_editor):
    Therapist = apps.get_model('scheduler', 'Therapist')
    for i, name in enumerate(SEED):
        Therapist.objects.get_or_create(name=name, defaults={'order': i})


def unseed(apps, schema_editor):
    Therapist = apps.get_model('scheduler', 'Therapist')
    Therapist.objects.filter(name__in=SEED).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_therapists, unseed),
    ]
