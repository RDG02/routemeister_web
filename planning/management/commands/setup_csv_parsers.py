from django.core.management.base import BaseCommand
from planning.models import CSVParserConfig


class Command(BaseCommand):
    help = 'Setup standaard CSV parser configuraties'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Setup standaard CSV parser configuraties...')
        
        # Fahrdlist configuratie
        fahrdlist_config, created = CSVParserConfig.objects.get_or_create(
            naam='Fahrdlist',
            defaults={
                'actief': True,
                'prioriteit': 10,
                'bestandsnaam_patroon': 'fahrdlist.*\\.csv',
                'header_keywords': 'kunde,termin,fahrer,nachname,vorname,straße,stadt,plz,telefon,mobil',
                'kolom_mapping': {
                    'patient_id': 0,
                    'achternaam': 1,
                    'voornaam': 2,
                    'adres': 3,
                    'plaats': 4,
                    'postcode': 5,
                    'telefoon1': 6,
                    'telefoon2': 7,
                    'datum': 8,
                    'start_tijd': 9,
                    'eind_tijd': 10
                },
                'datum_formaten': 'DD-MM-YYYY,DD.MM.YYYY,DD/MM/YYYY',
                'tijd_formaten': 'HHMM,HH:MM,H:MM',
                'beschrijving': 'Duits CSV formaat voor Fahrdlist bestanden met patiëntgegevens'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Fahrdlist configuratie aangemaakt'))
        else:
            self.stdout.write('ℹ️ Fahrdlist configuratie bestond al')
        
        # Routemeister configuratie
        routemeister_config, created = CSVParserConfig.objects.get_or_create(
            naam='Routemeister',
            defaults={
                'actief': True,
                'prioriteit': 5,
                'bestandsnaam_patroon': 'routemeister.*\\.csv',
                'header_keywords': 'patient,achternaam,voornaam,adres,plaats,postcode,telefoon,afspraak,behandeling',
                'kolom_mapping': {
                    'patient_id': 1,
                    'achternaam': 2,
                    'voornaam': 3,
                    'adres': 6,
                    'plaats': 8,
                    'postcode': 9,
                    'telefoon1': 10,
                    'telefoon2': 11,
                    'datum': 15,
                    'start_tijd': 17,
                    'eind_tijd': 18
                },
                'datum_formaten': 'DD-MM-YYYY,DD.MM.YYYY,DD/MM/YYYY',
                'tijd_formaten': 'HHMM,HH:MM,H:MM',
                'beschrijving': 'Nederlands CSV formaat voor Routemeister bestanden'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Routemeister configuratie aangemaakt'))
        else:
            self.stdout.write('ℹ️ Routemeister configuratie bestond al')
        
        # Generic configuratie
        generic_config, created = CSVParserConfig.objects.get_or_create(
            naam='Generic CSV',
            defaults={
                'actief': True,
                'prioriteit': 1,
                'header_keywords': 'id,naam,adres,telefoon,datum,tijd',
                'kolom_mapping': {
                    'patient_id': 0,
                    'achternaam': 1,
                    'voornaam': 2,
                    'adres': 3,
                    'plaats': 4,
                    'postcode': 5,
                    'telefoon1': 6,
                    'telefoon2': 7,
                    'datum': 8,
                    'start_tijd': 9,
                    'eind_tijd': 10
                },
                'datum_formaten': 'DD-MM-YYYY,DD.MM.YYYY,DD/MM/YYYY,YYYY-MM-DD',
                'tijd_formaten': 'HHMM,HH:MM,H:MM,HH:MM:SS',
                'beschrijving': 'Generieke CSV configuratie voor standaard patiëntgegevens'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Generic CSV configuratie aangemaakt'))
        else:
            self.stdout.write('ℹ️ Generic CSV configuratie bestond al')
        
        self.stdout.write(self.style.SUCCESS('🎉 CSV parser configuraties setup voltooid!'))
        self.stdout.write('📝 Ga naar /admin/planning/csvparserconfig/ om configuraties aan te passen')
