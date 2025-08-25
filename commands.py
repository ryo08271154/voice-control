class VoiceCommand:
    def __init__(self, user_input_text, action_type="default", reply_text=""):
        self.user_input_text = user_input_text
        self.action_type = action_type
        self.reply_text = reply_text
        self.flet_view = None