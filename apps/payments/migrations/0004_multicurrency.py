from decimal import Decimal

from django.db import migrations, models


def seed_exchange_rates(apps, schema_editor):
    ExchangeRate = apps.get_model("payments", "ExchangeRate")
    defaults = [
        ("KES", Decimal("129.0000")),
        ("SOS", Decimal("570.0000")),
        ("SLSH", Decimal("570.0000")),
        ("ETB", Decimal("56.0000")),
    ]
    for code, rate in defaults:
        ExchangeRate.objects.get_or_create(
            from_currency="USD",
            to_currency=code,
            defaults={"rate": rate, "is_active": code == "KES"},
        )


def backfill_payment_usd(apps, schema_editor):
    Payment = apps.get_model("payments", "Payment")
    for payment in Payment.objects.select_related("level").all():
        if payment.amount_usd is None:
            payment.amount_usd = payment.level.price if payment.level_id else payment.amount
        if not payment.currency:
            payment.currency = "KES"
        payment.save(update_fields=["amount_usd", "currency"])


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_instant_payment_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExchangeRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("from_currency", models.CharField(default="USD", max_length=3)),
                ("to_currency", models.CharField(max_length=4)),
                ("rate", models.DecimalField(decimal_places=4, help_text="1 USD equals this many units of to_currency", max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["to_currency"],
                "unique_together": {("from_currency", "to_currency")},
            },
        ),
        migrations.AddField(
            model_name="payment",
            name="amount_usd",
            field=models.DecimalField(blank=True, decimal_places=2, help_text="Base course price in USD", max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="payment",
            name="currency",
            field=models.CharField(default="USD", max_length=4),
        ),
        migrations.AddField(
            model_name="payment",
            name="exchange_rate",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True),
        ),
        migrations.RunPython(seed_exchange_rates, migrations.RunPython.noop),
        migrations.RunPython(backfill_payment_usd, migrations.RunPython.noop),
    ]
