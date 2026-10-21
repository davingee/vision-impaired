-- Send one text through Messages to an existing conversation.
-- Reading uses chat.db instead: Messages' scripting dictionary exposes no message text.
-- argv: chat id (chat.guid from chat.db), path to a UTF-8 file holding the text.
on run argv
	set chatId to item 1 of argv
	set body to read (POSIX file (item 2 of argv)) as «class utf8»
	tell application "Messages" to send body to chat id chatId
	return "handed_to_messages"
end run
