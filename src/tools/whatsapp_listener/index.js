import { Boom } from '@hapi/boom'
import makeWASocket, { useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys'
import qrcode from 'qrcode-terminal'
import Pino from "pino"
import fs from 'fs'

async function whatsapp_calling_message() {
    const { state, saveCreds } = await useMultiFileAuthState("auth") // saves session files

    const sock = makeWASocket({
        auth: state,
        logger: Pino({ level: 'silent' }) // Reduce log spam
    });

    sock.ev.on("connection.update", (update) => {
        const { qr, connection, lastDisconnect } = update
        
        if (qr) {
            console.log('Scan this QR code:')
            qrcode.generate(qr, { small: true })
        }
        
        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error instanceof Boom)
                ? lastDisconnect.error.output?.statusCode !== DisconnectReason.loggedOut
                : true
            
            console.log('Connection closed. Reason:', lastDisconnect?.error?.message)
            
            if (shouldReconnect) {
                console.log('Reconnecting in 5 seconds...')
                setTimeout(() => whatsapp_calling_message(), 5000) // Fixed: use correct function name
            } else {
                console.log('Logged out. Please delete auth folder and scan QR again.')
            }
        } else if (connection === 'open') {
            console.log('✅ Connected successfully!')
        }
    })

    sock.ev.on("creds.update", saveCreds)

    sock.ev.on("messages.upsert", async m => {
        const msg = m.messages[0];
        if (!msg.message) return;

        // Get sender name, remoteJid, and group info
        const senderName = msg.pushName || msg.key.participant || msg.key.remoteJid;
        const remoteJid = msg.key.remoteJid;
        let chatType = "Personal";
        let chatName = remoteJid;
        let groupImage = null;

        if (remoteJid.endsWith("@g.us")) {
            chatType = "Group";
            try {
                const metadata = await sock.groupMetadata(remoteJid);
                chatName = metadata.subject;
                groupImage = await sock.profilePictureUrl(remoteJid, 'image');
            } catch (err) {
                chatName = remoteJid;
            }
        } else {
            if (msg.chat) {
                chatName = msg.chat.name || remoteJid;
            } else if (msg.key.remoteJid) {
                chatName = msg.key.remoteJid;
            }
        }

        // Get message text
        let text = "";
        let mentionedNames = [];
        let groupMetadata = null;
        if (remoteJid.endsWith("@g.us")) {
            try {
                groupMetadata = await sock.groupMetadata(remoteJid);
            } catch (err) {
                groupMetadata = null;
            }
        }
        if (msg.message.conversation) {
            text = msg.message.conversation;
        } else if (msg.message.extendedTextMessage && msg.message.extendedTextMessage.text) {
            text = msg.message.extendedTextMessage.text;
            // Resolve mentionedJid to names using groupMetadata
            const contextInfo = msg.message.extendedTextMessage.contextInfo;
            if (contextInfo && contextInfo.mentionedJid && groupMetadata) {
                for (const jid of contextInfo.mentionedJid) {
                    let name = jid;
                    const participant = groupMetadata.participants.find(p => p.id === jid);
                    if (participant) {
                        name = participant.name || participant.notify || jid;
                    }
                    mentionedNames.push({jid, name});
                    // Replace @jid in text with @name
                    text = text.replace(new RegExp(`@${jid.split('@')[0]}`, 'g'), `@${name}`);
                }
            }
        } else if (msg.message.imageMessage && msg.message.imageMessage.caption) {
            text = msg.message.imageMessage.caption;
        }

        // Get timestamp
        const timestamp = msg.messageTimestamp ? new Date(msg.messageTimestamp * 1000) : new Date();
        const timeString = timestamp.toLocaleString();

        // Build JSON object
        const messageInfo = {
            time: timeString,
            chatType,
            chatName,
            senderName,
            text,
            groupImage,
            remoteJid,
            mentionedNames
        };

        // Append to messages.json
        const filePath = './messages.json';
        let messages = [];
        if (fs.existsSync(filePath)) {
            try {
                messages = JSON.parse(fs.readFileSync(filePath));
            } catch (e) {
                messages = [];
            }
        }
        messages.push(messageInfo);
        fs.writeFileSync(filePath, JSON.stringify(messages, null, 2));
    });
}
whatsapp_calling_message()

