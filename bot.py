import telebot
from PIL import Image, ImageOps
import io
from telebot import types

TOKEN = '<token goes here>'
bot = telebot.TeleBot(TOKEN)

user_states = {}  # тут будем хранить информацию о действиях пользователя

# набор символов из которых составляем изображение
ASCII_CHARS = '@%#*+=-:. '


def mirror_image(image_stream, direction='horizontal'):
    image = Image.open(image_stream)

    if direction.lower() == 'horizontal':
        mirrored_image = image.transpose(Image.FLIP_LEFT_RIGHT)
    elif direction.lower() == 'vertical':
        mirrored_image = image.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        raise ValueError("Invalid direction specified. Use 'horizontal' or 'vertical'.")

    output_stream = io.BytesIO()
    mirrored_image.save(output_stream, format="PNG")
    output_stream.seek(0)
    return output_stream

def get_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    mirror_horizontal_btn = types.InlineKeyboardButton("Mirror Horizontally", callback_data="mirror_horizontal")
    mirror_vertical_btn = types.InlineKeyboardButton("Mirror Vertically", callback_data="mirror_vertical")
    keyboard.add(pixelate_btn, ascii_btn, mirror_horizontal_btn, mirror_vertical_btn)
    return keyboard

def resize_image(image, new_width=100):
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def grayify(image):
    return image.convert("L")


def image_to_ascii(image_stream, new_width=40, ascii_chars=ASCII_CHARS):
    # Переводим в оттенки серого
    image = Image.open(image_stream).convert('L')

    # меняем размер сохраняя отношение сторон
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(
        aspect_ratio * new_width * 0.55)  # 0,55 так как буквы выше чем шире
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized)
    img_width = img_resized.width

    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art


def pixels_to_ascii(image, ascii_chars=ASCII_CHARS):
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        index = pixel * len(ascii_chars) // 256
        characters += ascii_chars[index]
    return characters


# Огрубляем изображение
def pixelate_image(image, pixel_size):
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image

def invert_colors(image):
    return ImageOps.invert(image)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Send me an image, and I'll provide options for you!")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "Choose your character set for ASCII art:",
                 reply_markup=get_character_set_keyboard())

    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}

@bot.message_handler(regexp=r'^([@%#*+=-:. ]+)$')
def handle_character_set(message):
    user_states[message.chat.id]['character_set'] = message.text
    bot.reply_to(message, "Great choice Now, let's convert your image.")


def get_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    keyboard.add(pixelate_btn, ascii_btn)
    return keyboard


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "pixelate":
        bot.answer_callback_query(call.id, "Pixelating your image...")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        bot.answer_callback_query(call.id, "Converting your image to ASCII art...")
        ascii_and_send(call.message)
    elif call.data.startswith("mirror_"):
        direction = call.data.split("_")[1]
        bot.answer_callback_query(call.id, f"Mirroring your image {direction}ly...")
        mirrored_image_stream = mirror_image(user_states[call.message.chat.id]['photo'], direction)
        bot.send_photo(call.message.chat.id, mirrored_image_stream)

def pixelate_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    pixelated = pixelate_image(image, 20)
    inverted_pixelated = invert_colors(pixelated)

    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def ascii_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image_stream = io.BytesIO(downloaded_file)
    ascii_chars = user_states[message.chat.id].get('character_set', ASCII_CHARS)
    ascii_art = image_to_ascii(image_stream, new_width=len(ascii_chars), ascii_chars=ascii_chars)
    bot.send_message(message.chat.id, ascii_art)


bot.polling(none_stop=True)


bot.polling(none_stop=True)
