import telebot
from PIL import Image, ImageOps
import io
from telebot import types
import random

COMPLIMENTS = [
    "You're amazing!",
    "Your smile brightens my day.",
    "I'm so grateful to have you in my life.",
    "You're doing great work!",
    "Your kindness is inspiring."
]

TOKEN = '7235559625:AAF0vJ5RUFZJBocFE2QGpk-8EJH10jW-4-Q'
bot = telebot.TeleBot('7235559625:AAF0vJ5RUFZJBocFE2QGpk-8EJH10jW-4-Q')

user_states = {}  # тут будем хранить информацию о действиях пользователя

# набор символов из которых составляем изображение
ASCII_CHARS = '@%#*+=-:. '

def get_random_compliment():
    return random.choice(COMPLIMENTS)

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

def convert_to_heatmap(image):
    heatmap_image = Image.new("RGB", image.size)
    grayscale_pixels = image.getdata()
    color_indices = []
    for pixel_value in grayscale_pixels:
        color_index = int(pixel_value * 255 / 255)
        color_indices.append(color_index)

    heatmap_image.putdata([
        ImageOps.colorize(
            Image.new("L", (1, 1), pixel_value),
            Image.new("L", (1, 1), (0, 0, 255)),
            Image.new("L", (1, 1), (255, 0, 0))
        ).resize(image.size).getdata()[0]
        for pixel_value in color_indices
    ])

    return heatmap_image

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

def resize_for_sticker(image_stream, max_size=512):

    image = Image.open(image_stream)
    original_width, original_height = image.size

    scale_factor = max_size / max(original_width, original_height)

    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)

    new_width = min(new_width, max_size)
    new_height = min(new_height, max_size)

    resized_image = image.resize((new_width, new_height))

    output_stream = io.BytesIO()
    resized_image.save(output_stream, format="PNG")
    output_stream.seek(0)

    return output_stream

def flip_coin():
    return random.choice(['Heads', 'Tails'])


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Send me an image, and I'll provide options for you!")

@bot.message_handler(commands=['random_compliment'])
def send_random_compliment(message):
    compliment = get_random_compliment()
    bot.reply_to(message, compliment)

@bot.message_handler(commands=['flip'])
def send_flip_result(message):
    result = flip_coin()
    bot.reply_to(message, result)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "Choose your character set for ASCII art:",
                 reply_markup=get_character_set_keyboard())

    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}

@bot.callback_query_handler(lambda call: call.data in ['@', '%', '#', '*', '+', '=', '-', ':', '.'])
def handle_character_set(call):
    user_states[message.chat.id]['character_set'] = call.data
    bot.answer_callback_query(call.id, "Character set updated.")

def get_character_set_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    character_sets = ['@', '%', '#', '*', '+', '=', '-', ':', '.', ' ']
    for char_set in character_sets:
        button = types.InlineKeyboardButton(char_set, callback_data=f"{char_set}")
        keyboard.row(button)
    return keyboard


def get_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    keyboard.add(pixelate_btn, ascii_btn)
    heatmap_btn = types.InlineKeyboardButton("Heat Map", callback_data="heatmap")
    resize_sticker_btn = types.InlineKeyboardButton("Resize Sticker", callback_data="resize_sticker")
    keyboard.add(pixelate_btn, ascii_btn, mirror_horizontal_btn, mirror_vertical_btn, heatmap_btn)
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
    elif call.data == "heatmap":
        bot.answer_callback_query(call.id, "Generating heat map...")
        heatmap_image_stream = convert_to_heatmap(user_states[call.message.chat.id]['photo'])
        bot.send_photo(call.message.chat.id, heatmap_image_stream)
    elif call.data == "resize_sticker":
        bot.answer_callback_query(call.id, "Resizing your image for a sticker...")
        resized_image_stream = resize_for_sticker(user_states[call.message.chat.id]['photo'], max_size=512)
        bot.send_photo(call.message.chat.id, resized_image_stream)
    elif call.data in ['@', '%', '#', '*', '+', '=', '-', ':', '.']:
        user_states[call.message.chat.id]['character_set'] = call.data
        bot.answer_callback_query(call.id, "Character set updated.")

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
