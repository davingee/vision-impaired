// JXA uses Mail's installed scripting dictionary. Sends only replies, only when mail.py
// confirms the user said yes.
ObjC.import("Foundation");

function run(argv) {
    const data = $.NSData.dataWithContentsOfFile(argv[0]);
    if (!data) throw Error("Cannot read request.");
    const input = ObjC.unwrap($.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding));
    const request = JSON.parse(input);
    const mail = Application("Mail");
    function metadata(message) {
        return {id: message.id(), subject: message.subject(), sender: message.sender(),
                received: message.dateReceived().toISOString()};
    }
    if (request.action === "list") {
        const limit = request.limit;
        if (!Number.isInteger(limit) || limit < 1 || limit > 20) throw Error("Limit must be 1–20.");
        const ids = mail.inbox.messages.id();
        const dates = mail.inbox.messages.dateReceived();
        const ranked = ids.map((id, i) => ({id: id, time: dates[i].getTime()}))
                          .sort((a, b) => b.time - a.time).slice(0, limit);
        // Totals too, so "here are 20" is never mistaken for "you have 20".
        return JSON.stringify({scope: "combined inbox", total_in_inbox: ids.length,
            unread_in_inbox: mail.inbox.unreadCount(), showing_newest: ranked.length,
            messages: ranked.map(item => metadata(mail.inbox.messages.whose({id: item.id})()[0]))});
    }
    let message;
    if (request.id === null || request.id === undefined) {
        if (request.action !== "read") throw Error("An exact inbox message ID is required.");
        const selection = mail.selection();
        if (selection.length !== 1) throw Error("Select exactly one Mail message, or supply an inbox message ID.");
        message = selection[0];
    } else {
        if (!Number.isInteger(request.id) || request.id < 0) throw Error("Invalid message ID.");
        const found = mail.inbox.messages.whose({id: request.id})();
        if (found.length !== 1) throw Error("Message is not uniquely present in the inbox. Refresh the message list.");
        message = found[0];
    }
    if (request.action === "read") {
        return JSON.stringify(Object.assign(metadata(message), {body: message.content()}));
    }
    if (request.action === "draft") {
        if (typeof request.text !== "string" || !request.text.trim() || request.text.length > 100000)
            throw Error("Reply must contain 1–100,000 characters.");
        const draft = mail.reply(message, {openingWindow: true, replyToAll: false});
        draft.content = request.text + "\n\n" + draft.content();
        mail.save(draft);
        return JSON.stringify({status: "draft_created", sent: false, original_id: request.id,
            draft_id: draft.id(), subject: draft.subject(),
            to: draft.toRecipients.address(), body: draft.content()});
    }
    if (request.action === "send") {
        if (request.confirmed !== true) throw Error("Reply not confirmed by the user.");
        if (typeof request.text !== "string" || !request.text.trim() || request.text.length > 20000)
            throw Error("Reply must contain 1–20,000 characters.");
        const reply = mail.reply(message, {openingWindow: false, replyToAll: false});
        reply.content = request.text + "\n\n" + reply.content();
        const subject = reply.subject(), to = reply.toRecipients.address();
        const started = new Date(Date.now() - 60000);
        mail.send(reply);
        // Mail gives no result; the Sent mailbox shows whether it really went out.
        for (let i = 0; i < 20; i++) {
            delay(1);
            const sent = mail.sentMailbox.messages.whose({subject: subject})();
            if (sent.some(m => m.dateSent() >= started))
                return JSON.stringify({status: "sent", to: to, subject: subject});
        }
        return JSON.stringify({status: "pending", to: to, subject: subject,
            note: "Handed to Mail; not yet in the Sent mailbox."});
    }
    throw Error("Unknown Mail action.");
}
