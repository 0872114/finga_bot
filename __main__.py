import os
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from libs import ChordParser, Tuning
from io import BytesIO


def noexceptions(fn):
    def wrapper(*args, **kwargs):
        try:
            res = fn(*args, **kwargs)
        except Exception as e:
            print(e)
            return None
        else:
            return res
    return wrapper

class Bot:
    user_settings = dict()

    @classmethod
    @noexceptions
    def help(cls, update: Update, context: CallbackContext) -> None:
        help_text = """
        Input a chord name, eg: Am7 or Dsus4/B
        
        Use comma (",") to input multiply chords, e.g.: "Am, Dm, E" 
        Commands:
          /help - this help ;)
          /tune <tuning> - change tuning, eg, "/tune EADG" for 4-string bass guitar
          /tune default - returns tuning to classic EBGDAE
            
        """
        update.message.reply_text(help_text)

    @classmethod
    @noexceptions
    def tune(cls, update: Update, context: CallbackContext) -> None:
        user = update.effective_user.id
        if not len(context.args):
            update.message.reply_text('tuning cannot be empty')
            return

        try:
            tuning_name = context.args[0].strip()
            if tuning_name.upper() == 'DEFAULT':
                if cls.user_settings.get(user, {}).get('tuning') is not None:
                    del cls.user_settings[user]['tuning']
                update.message.reply_text('tuning is set to default (EBGDAE)')
                return

            tuning = Tuning(name=tuning_name)
        except ValueError:
            response = 'invalid tuning {}'.format(context.args[0])
        else:
            if cls.user_settings.get(user) is None:
                cls.user_settings[user] = dict()
            cls.user_settings[user]['tuning'] = tuning
            response = 'tuning is set to {}'.format(tuning)
        update.message.reply_text(response)

    @classmethod
    @noexceptions
    def reverse(cls, update: Update, context: CallbackContext) -> None:
        user = update.effective_user.id
        if cls.user_settings.get(user) is None:
            cls.user_settings[user] = dict(reverse=False)
        elif cls.user_settings.get(user, {}).get('reverse') is None:
            cls.user_settings[user]['reverse'] = False
        cls.user_settings[user]['reverse'] = not cls.user_settings[user]['reverse']
        reverse = cls.user_settings[user]['reverse']
        update.message.reply_text('fret is now {} mirrored'.format('' if reverse else 'not'))

    @classmethod
    @noexceptions
    def explain(cls, update: Update, context: CallbackContext) -> None:
        chord_names = update.message.text.split(',')
        user = update.effective_user.id
        tuning_name = ''
        tuning = cls.user_settings.get(user, {}).get('tuning')
        reverse = cls.user_settings.get(user, {}).get('reverse', False)
        if tuning is not None:
            tuning_name = ' (tuning: {})'.format(tuning.name)
        print('tuning for {} is {}'.format(user, tuning))
        for chord_name in chord_names:
            chord_name = chord_name.strip()
            try:
                title, result = ChordParser.explain_draw(chord_name, tuning=tuning, reverse=reverse)
            except (IndexError) as e:
                print(e, chord_name)
                result = '{} is not a valid chord name'.format(chord_name)
                update.message.reply_text(result)
            else:
                update.message.reply_text(title + tuning_name)
                bio = BytesIO()
                bio.name = 'schema.jpeg'
                result.save(bio, 'JPEG')
                bio.seek(0)
                update.message.reply_photo(bio)


def main() -> None:
    """Start the bot."""
    updater = Updater(os.environ.get("bot_token"))
    dispatcher = updater.dispatcher

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, Bot.explain))

    dispatcher.add_handler(CommandHandler("start", Bot.help))
    dispatcher.add_handler(CommandHandler("help", Bot.help))
    dispatcher.add_handler(CommandHandler("tune", Bot.tune))
    dispatcher.add_handler(CommandHandler("tuning", Bot.tune))
    dispatcher.add_handler(CommandHandler("reverse", Bot.reverse))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

