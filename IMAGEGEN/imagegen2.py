from datetime import datetime
import sys
from PIL import Image, ImageDraw, ImageFont
import json


class ImageGenerator:
    font_huge = ImageFont.load_default()
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()

    def __init__(self):
        # Configdaten importieren und auf Grundvariablen anwenden:

        try:
            with open('config.json', 'r') as config_file:
                config_data = json.load(config_file)
                self.cfg = config_data['config'][2]
        except OSError as e:
            print("Configfile not found - Please check the File!", e)
            return sys.exit()

        cfg = self.cfg
        # Bildparameter
        self.size = (cfg['image_size'][0], cfg['image_size'][1])
        self.image_path = cfg['image_path']
        self.maintenance_path = cfg['maintenance_path']

        self.background_color = cfg['background_color']  # Weiß

        # Standard-Font in Variable übertragen:
        self.font = cfg['standard_font']

        # Rechteckdimensionen einfügen:
        self.lesson_rect_color = cfg['lesson_rect_color']
        self.lesson_rect_height = cfg['lesson_rect_height']
        self.upper_margin = cfg['upper_margin']
        self.bottom_margin = cfg['bottom_margin']
        self.outside_margin = cfg['outside_margin']
        self.lesson_rect_spacing = cfg['lesson_rect_spacing']
        self.lesson_rect_outline_color = cfg['lesson_rect_outline_color']
        self.lesson_rect_outline_width = cfg['lesson_rect_outline_width']
        self.double_lesson_multiplier = cfg['double_lesson_multiplier']

        # Standard Bottom Text aus Config abrufen
        self.bottom_text = cfg['bottom_text']
        self.inMaintenanceMode = cfg['inMaintenanceMode']

        # Schriftart laden
        try:
            self.font_huge = ImageFont.truetype(self.font, 64)  # Riesenschrift
            self.font_large = ImageFont.truetype(self.font, 48)  # Große Schrift für Fächer
            self.font_medium = ImageFont.truetype(self.font, 32)  # Mittlere Schrift für Klassen und Lehrer
            self.font_small = ImageFont.truetype(self.font, 20)  # Kleine Schrift für "generiert um" und Zeiten
        except IOError as e:
            print("Fonts konnten nicht geladen werden.", e)

    def get_logo_image(self):
        # Logo laden und positionieren
        path = self.cfg['tbz_logo_path']
        try:
            logo = Image.open(path).convert('L')  # Logo in Graustufen laden
            return logo.resize((self.cfg['logo_size'][0], self.cfg['logo_size'][1]))  # Logo auf gewünschte Größe skalieren
        except FileNotFoundError:
            print(f"Logo-Datei in {path} nicht gefunden. Überspringe das Logo.")
            return Image.new('L', (0,0), 0)

    @staticmethod
    def get_hour_and_minutes(time):
        hour = time[:-2]
        minutes = time[2:]

        return hour, minutes

    """formats the raw time depending on start or endtime"""
    def format_time(self, time, is_start_time):
        hour, minutes = self.get_hour_and_minutes(time)

        formatted_time = f'{hour}:{minutes}'
        if is_start_time:
            formatted_time += ' -'

        return formatted_time

    def get_lesson_duration_in_minutes(self, lesson):
        start_time = lesson['start']
        end_time = lesson['end']

        start_hour, start_minutes = self.get_hour_and_minutes(start_time)
        start_duration = start_hour * 60 + start_minutes

        end_hour, end_minutes = self.get_hour_and_minutes(end_time)
        end_duration = end_hour * 60 + end_minutes

        return end_duration - start_duration

    def generate_image(self, room, lessons, bottom_text=None):
        image = Image.new('L', self.size, self.background_color)
        draw = ImageDraw.Draw(image)

        # draw logo
        image.paste(self.get_logo_image(), (int(self.outside_margin), int(self.outside_margin)))

        # draw room and day
        self.draw_room_and_day(draw, room, self.font_large, 0)

        # draw bottom text
        if bottom_text is None:
            bottom_text = self.bottom_text

        draw.text((self.outside_margin, self.size[1] - self.outside_margin), bottom_text, font=self.font_small, anchor="lm")

        self.draw_date_generated(draw, self.font_small, 0)

        # draw lesson rects
        if len(lessons) == 0:
            # keine stunden zum Anzeigen
            draw.text((140, 240), "Heute kein weiterer Unterricht", font=self.font_large, fill=0)
            draw.text((270, 320), "in diesem Raum", font=self.font_large, fill=0)
            pass
        else:
            previous_lesson_image_height = 0
            double_lesson_amount = 0
            lesson_amount = len(lessons)

            for lesson in lessons:
                if lesson["is_double"]:
                    double_lesson_amount += 1
                    lesson_amount += self.double_lesson_multiplier - 1
                pass


            for i, lesson in enumerate(lessons):
                """
                change spacing according to amount of lessons
                <= 4 -> spacing[0]
                > 4 -> spacing[1]
                >= 6 -> spacing[2]
                """
                spacing = self.lesson_rect_spacing[0]
                if lesson_amount <= 4:
                    spacing = self.lesson_rect_spacing[0]
                if lesson_amount > 4:
                    spacing = self.lesson_rect_spacing[1]
                if lesson_amount >= 6:
                    spacing = self.lesson_rect_spacing[2]


                lesson_image = self.generate_lesson_image(lesson, lesson_amount, double_lesson_amount, spacing)

                # paste lesson image on top of total image with offset depending on spacing and previous position of the lesson images
                image.paste(lesson_image, (self.outside_margin, self.upper_margin + previous_lesson_image_height + spacing * i))
                previous_lesson_image_height += lesson_image.height

        self.save_image(image, room)

    def save_image(self, image, room):
        # Überprüfen, ob der Wartungsmodus false oder true ist:
        # Bild nach Raumname in ROMMIMAGES speichern
        path = self.image_path.replace("%ROOM%", room)
        if self.inMaintenanceMode:
            path = self.maintenance_path
        image.save(path)


    def generate_lesson_image(self, lesson, lesson_amount, double_lesson_amount, spacing):
        width = self.size[0] - self.outside_margin * 2

        # total image height - height of text above - the needed spacing between the lessons
        height = int((self.size[1] - self.bottom_margin - self.upper_margin) / lesson_amount)

        # subtract spacing from height so the lessons dont move up once spacing is added
        height -= spacing

        # adjust for remaining spacing at the bottom and the extra spacing of the double lessons
        height += int(spacing / lesson_amount) + int(((spacing * self.double_lesson_multiplier) - spacing) * double_lesson_amount / lesson_amount)

        # check if lesson is double
        if lesson["is_double"]:
            height = int(height * self.double_lesson_multiplier)

        # create image
        image = Image.new('L', (width, height), self.background_color)
        draw = ImageDraw.Draw(image)

        # draw outline rectangle
        draw.rectangle([0,0,width,height], fill=self.lesson_rect_color, outline=self.lesson_rect_outline_color, width=self.lesson_rect_outline_width)

        # draw lesson texts
        self.draw_lesson_texts(lesson, draw, width, height)

        return image

    def draw_lesson_texts(self, lesson, draw, lesson_rect_width, lesson_rect_height):
        # draw lesson texts
        start_time = self.format_time(lesson['start'], True)
        end_time = self.format_time(lesson['end'], False)

        # change data of lesson text in here if needed
        lesson_text_data = [
            {
                'text': f'{start_time}\n{end_time}',
                'font': self.font_small,
                'color': 0,
            },
            {
                'text': lesson["class"],
                'font': self.font_medium,
                'color': 0,
            },
            {
                'text': lesson["subject"],
                'font': self.font_large,
                'color': 0,
            },
            {
                'text': lesson["teacher"],
                'font': self.font_medium,
                'color': 0,
            }
        ]

        text_amount = len(lesson_text_data)
        for i, lesson_text in enumerate(lesson_text_data):
            text = lesson_text['text']
            font = lesson_text['font']
            color = lesson_text['color']

            # align on x axis and center y axis
            x = lesson_rect_width - (lesson_rect_width // text_amount * (text_amount - i)) + (lesson_rect_width // text_amount // 2)
            y = lesson_rect_height // 2

            # check for multiline
            if '\n' in lesson_text['text']:
                draw.multiline_text((x, y), text, font=font, fill=color, anchor="mm")
            else:
                draw.text((x, y), text, font=font, fill=color, anchor="mm")

    def draw_room_and_day(self, draw, room, font, color):
        current_day_num = datetime.today().weekday()
        days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag",
                      "Sonntag"]

        room_day_text = f'{room} - {days[current_day_num]}'

        draw.text((self.size[0] - self.outside_margin, self.upper_margin // 2), room_day_text, font=font, fill=color, anchor='rm')

    def draw_date_generated(self, draw, font, color):
        # Aktuelle Zeit für den unteren Text
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M Uhr")

        # Text in der untersten Zeile
        footer_text = f"Generiert: {current_time}"

        # align with bottom right
        draw.text((self.size[0] - self.outside_margin, self.size[1] - self.outside_margin), footer_text, font=font, fill=color, anchor='rm')


if __name__ == "__main__":
    try:
        image_generator = ImageGenerator()
        image_generator.generate_image("2.310",  lessons=[{
                    "start": "0815",
                    "end": "1130",
                    "teacher": "SCJ",
                    "subject": "BInf",
                    "class": "BGT241",
                    "changed": False,
                    "is_double": True,
                },
                {
                    "start": "1145",
                    "end": "1315",
                    "teacher": "SID",
                    "subject": "IFT",
                    "class": "BGT241",
                    "changed": False,
                    "is_double": False,
                },{
                    "start": "1345",
                    "end": "1615",
                    "teacher": "WIB",
                    "subject": "DEU",
                    "class": "BGT241",
                    "changed": False,
                    "is_double": True,
                }
        ])
    except KeyboardInterrupt:
        # Behandle Strg+C und beende den Server sauber
        print("\nStrg+C erkannt. Server wird beendet...")


