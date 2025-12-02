import { Boom } from '@hapi/boom'
import makeWASocket, { useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys'
import qrcode from 'qrcode-terminal'
import Pino from "pino"
import fs from 'fs'

async function startWhatsAppListener() {
    const { state, saveCreds } = await useMultiFileAuthState("auth") // saves session files

    const sock = makeWASocket({
        auth: state,
        // use info level so we can see basic events; change back to 'silent' if too noisy
        logger: Pino({ level: 'info' })
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
                setTimeout(() => startWhatsAppListener(), 5000) // reconnect
            } else {
                console.log('Logged out. Please delete auth folder and scan QR again.')
            }
        } else if (connection === 'open') {
            console.log('✅ Connected successfully!')
        }
    })

    sock.ev.on("creds.update", saveCreds)

    sock.ev.on("messages.upsert", async m => {
        // Only process actual new incoming notifications
        if (m.type !== 'notify') return;
        const msg = m.messages[0];
        if (!msg || !msg.message) return;
        console.log("[whatsapp] notify id=", msg.key.id, "from=", msg.key.remoteJid);

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
        // Pull quoted text if present
        const quoted = msg.message?.extendedTextMessage?.contextInfo?.quotedMessage;
        let quotedText = '';
        if (quoted) {
            quotedText = quoted?.conversation || quoted?.extendedTextMessage?.text || quoted?.imageMessage?.caption || '';
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
        } else if (msg.message.videoMessage && msg.message.videoMessage.caption) {
            text = msg.message.videoMessage.caption;
        } else if (msg.message.documentMessage && msg.message.documentMessage.caption) {
            text = msg.message.documentMessage.caption;
        } else if (msg.message.audioMessage) {
            text = '[Audio]';
        } else if (msg.message.stickerMessage) {
            text = '[Sticker]';
        } else if (msg.message.pollCreationMessage) {
            text = `[Poll] ${msg.message.pollCreationMessage.name}`;
        } else if (msg.message.listMessage) {
            text = '[List message]';
        } else if (msg.message.buttonsMessage) {
            text = '[Buttons message]';
        } else if (msg.message.templateMessage) {
            text = '[Template message]';
        } else if (msg.message.reactionMessage) {
            text = `[Reaction] ${msg.message.reactionMessage.text || ''}`;
        } else if (msg.message.ephemeralMessage) {
            // unwrap ephemeral container
            const inner = msg.message.ephemeralMessage.message;
            if (inner?.extendedTextMessage?.text) {
                text = inner.extendedTextMessage.text;
            } else if (inner?.conversation) {
                text = inner.conversation;
            } else {
                text = '[Ephemeral message]';
            }
        }

        if (quotedText) {
            text = `${text} (quoted: ${quotedText})`;
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
        // Atomic write: write to temp then rename
        try {
            const tmpPath = filePath + '.tmp';
            fs.writeFileSync(tmpPath, JSON.stringify(messages, null, 2));
            fs.renameSync(tmpPath, filePath);
            console.log('[whatsapp] appended message count=', messages.length);
        } catch (writeErr) {
            console.error('[whatsapp] failed writing messages.json', writeErr);
        }
    });
}

// Export function to get all unread messages from messages.json
export function getAllUnreadMessages() {
    const filePath = './messages.json';
    
    if (!fs.existsSync(filePath)) {
        return { messages: [], count: 0 };
    }
    
    try {
        const messages = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        return {
            messages: messages,
            count: messages.length
        };
    } catch (e) {
        console.error('Error reading messages.json:', e);
        return { messages: [], count: 0, error: e.message };
    }
}
// Export start function so external process (Python) can control lifecycle
export { startWhatsAppListener };

// If executed directly (not imported by Python dynamic import), start automatically
try {
    // For ESM, process.argv[1] is the path to the script invoked
    const invoked = process.argv[1];
    if (invoked && invoked.endsWith('index.js')) {
        console.log('[whatsapp] direct run detected, starting listener...');
        startWhatsAppListener();
    }
} catch (e) {
    // Safe ignore
}

