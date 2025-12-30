def simple_chatbot_view(message):
    msg = message.lower()
    if(msg == "hello"):
        return "Hello! How can I assist you today?"
    elif "notification" in msg:
        return "You have 3 new notifications."
    else:
        return "I'm sorry, I didn't understand that. Can you please rephrase?"