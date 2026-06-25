# Generated manually for LegalPage model



from django.db import migrations, models





class Migration(migrations.Migration):



    dependencies = [

        ("cms", "0004_platform_introduction_video"),

    ]



    operations = [

        migrations.CreateModel(

            name="LegalPage",

            fields=[

                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),

                ("created_at", models.DateTimeField(auto_now_add=True)),

                ("updated_at", models.DateTimeField(auto_now=True)),

                (

                    "page_type",

                    models.CharField(

                        choices=[("privacy", "Privacy Policy"), ("terms", "Terms & Conditions")],

                        max_length=20,

                        unique=True,

                    ),

                ),

                ("title", models.CharField(max_length=200)),

                (

                    "body",

                    models.TextField(

                        blank=True,

                        help_text="Optional HTML. Leave blank to show the built-in default legal text.",

                    ),

                ),

                ("last_updated", models.DateField(auto_now=True)),

            ],

            options={

                "verbose_name": "Legal Page",

                "verbose_name_plural": "Legal Pages",

                "ordering": ["page_type"],

            },

        ),

    ]


