/* Loaded after app.js. Does not replace the user's existing CSS or graph controls. */
(() => {
    'use strict';

    let ready = false;
    let working = false;
    let activeId = null;
    let refreshTimer;

    const panel = el('details', 'panel history-panel');
    panel.id = 'history-panel';
    panel.open = true;
    const summary = el('summary');
    const count = el('span', 'history-count', '');
    summary.append(el('span', '', 'השיחות שלי'), count);

    const body = el('div', 'history-body');
    const toolbar = el('div', 'history-toolbar');
    const refresh = el('button', 'text-button', 'רענון הרשימה ↻');
    refresh.type = 'button';
    refresh.id = 'history-refresh';
    toolbar.append(el('span', '', 'השיחות של הדפדפן הזה'), refresh);
    const list = el('div', 'history-list');
    list.id = 'history-list';
    list.setAttribute('aria-label', 'שיחות שמורות');
    const notice = el('p', 'history-notice', 'טוען שיחות…');
    notice.id = 'history-notice';
    notice.setAttribute('role', 'status');
    body.append(toolbar, list, notice);
    panel.append(summary, body);
    document.querySelector('.lab-column').prepend(panel);

    const dateFormat = new Intl.DateTimeFormat('he-IL', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });

    function isBusy() {
        return !ready || working || state.busy || $('run-tool').disabled;
    }

    function updateButtons() {
        const disabled = isBusy();
        panel.querySelectorAll('button').forEach(button => { button.disabled = disabled; });
    }

    function showConversation(data) {
        activeId = data.active_id;
        $('messages').replaceChildren();
        $('message').value = '';
        if (data.messages.length) {
            data.messages.forEach(message => renderMessage(message.role, message.content, message.payload));
        } else {
            const welcome = renderMessage('assistant', 'התחלנו שיחה חדשה. מה תרצו ללמוד?');
            welcome.id = 'welcome';
        }
    }

    async function loadList() {
        const data = await api('/conversations');
        // Another tab may have switched the shared browser session.
        if (activeId && activeId !== data.active_id) {
            const draft = $('message').value;
            showConversation(await api(`/conversations/${data.active_id}/open`, {}));
            $('message').value = draft;
            if (draft.trim()) toast('השיחה הפעילה השתנתה בלשונית אחרת. הטיוטה נשמרה; בדקו את השיחה לפני השליחה.');
        }
        activeId = data.active_id;
        list.replaceChildren();
        count.textContent = String(data.conversations.length);
        for (const conversation of data.conversations) {
            const row = el('div', 'history-row');
            const open = el('button', 'history-open');
            open.type = 'button';
            open.dataset.conversationId = conversation.id;
            open.title = conversation.title;
            const title = el('span', 'history-title', conversation.title);
            title.dir = 'auto';
            const date = el('time', 'history-date', dateFormat.format(new Date(conversation.updated_at)));
            date.dateTime = conversation.updated_at;
            open.append(title, date);
            if (conversation.id === activeId) {
                row.classList.add('active');
                open.setAttribute('aria-current', 'true');
            }
            open.onclick = () => {
                if (conversation.id === activeId || isBusy() || !allowSwitch()) return;
                perform(async () => {
                    showConversation(await api(`/conversations/${conversation.id}/open`, {}));
                    await loadList();
                    $('message').focus();
                });
            };
            const remove = el('button', 'history-delete', 'מחיקה');
            remove.type = 'button';
            remove.setAttribute('aria-label', `מחיקת השיחה: ${conversation.title}`);
            remove.onclick = () => {
                if (isBusy()) return;
                const draftNote = conversation.id === activeId && $('message').value.trim()
                    ? '\nגם הטיוטה שלא נשלחה תימחק.' : '';
                if (!window.confirm(`למחוק את השיחה ״${conversation.title}״?\nההודעות ותוצאות הכלים שלה יימחקו לצמיתות.${draftNote}`)) return;
                perform(async () => {
                    const data = await api(`/conversations/${conversation.id}/delete`, {});
                    if (conversation.id === activeId) showConversation({active_id: data.active_id, messages: []});
                    await loadList();
                });
            };
            row.append(open, remove);
            list.append(row);
        }
        notice.textContent = data.conversations.length ? '' : 'עדיין אין שיחות שמורות.';
        updateButtons();
    }

    function allowSwitch() {
        return !$('message').value.trim() || window.confirm('יש טיוטה שלא נשלחה. לעבור לשיחה אחרת ולוותר על הטיוטה?');
    }

    async function perform(action) {
        if (isBusy()) return;
        clearTimeout(refreshTimer);
        working = true;
        state.busy = true;
        const controls = ['send', 'new-chat', 'explain-tool', 'run-tool'];
        controls.forEach(id => { $(id).disabled = true; });
        $('message').readOnly = true;
        updateButtons();
        try {
            await action();
        } catch (error) {
            notice.textContent = error.message;
            toast(error.message);
        } finally {
            working = false;
            state.busy = false;
            controls.forEach(id => { $(id).disabled = false; });
            $('message').readOnly = false;
            updateButtons();
        }
    }

    function scheduleRefresh() {
        if (isBusy()) return;
        clearTimeout(refreshTimer);
        refreshTimer = setTimeout(() => perform(loadList), 100);
    }

    refresh.onclick = () => perform(loadList);
    $('new-chat').onclick = () => {
        if (isBusy() || !allowSwitch()) return;
        perform(async () => {
            showConversation(await api('/conversations/new', {}));
            await loadList();
            $('message').focus();
        });
    };

    // Existing sendMessage() updates the message container; no changes to it are needed.
    new MutationObserver(scheduleRefresh).observe($('messages'), {childList: true});
    const busyObserver = new MutationObserver(updateButtons);
    ['new-chat', 'run-tool'].forEach(id => busyObserver.observe($(id), {
        attributes: true, attributeFilter: ['disabled']
    }));
    window.addEventListener('focus', scheduleRefresh);
    updateButtons();

    Promise.resolve(window.algotutorReady).then(() => {
        ready = true;
        perform(async () => {
            await loadList();
            // Load the entire conversation, including histories longer than 100 messages.
            const current = await api(`/conversations/${activeId}/open`, {});
            if (current.messages.length || !$('welcome')) showConversation(current);
        });
    });
})();
