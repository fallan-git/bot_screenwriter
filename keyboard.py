from telebot import types
from text import Settings

hideKeyboard = types.ReplyKeyboardRemove()

markup_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
markup_menu.add("/help", "/story")

markup_help = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
markup_help.add("/tokens", "/story")

markup_genre = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
markup_genre.add(*list(Settings.keys()))

markup_start = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
markup_start.add("/generate")
