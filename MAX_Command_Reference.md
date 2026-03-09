# MAX AI Assistant — Complete Command Reference

> **Version:** Phase-1 MVP  
> **Modes:** USER (default) · PRIME (authenticated)  
> **Input:** Text (CLI) or Voice

---

## 🔐 Authentication & Mode Switching

These commands are available in **any mode**.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Set passphrase** | `set passphrase mySecret123` | `Passphrase saved successfully. Use 'enter prime <phrase>' to activate Prime mode.` |
| 2 | **Enter Prime Mode** | `enter prime mySecret123` | `PRIME mode activated. Welcome.` |
| 3 | **Enter Prime (no phrase)** | `enter prime` | `Passphrase required. Say: 'enter prime <your passphrase>'` |
| 4 | **Enter Prime (wrong)** | `enter prime wrongpass` | `Incorrect passphrase. PRIME mode NOT activated.` |
| 5 | **Exit Prime Mode** | `exit prime` | `Switched back to USER mode.` |
| 6 | **Switch to User Mode** | `user mode` | `Switched back to USER mode.` |

---

## 🌐 Web — Search & Browse

Available in **USER mode** and **PRIME mode**.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Web search** | `search for machine learning` | Opens DuckDuckGo/Google with the query |
| 2 | **Google search** | `google Python tutorial` | Opens Google with the query |
| 3 | **YouTube search** | `search youtube for lofi music` | Opens YouTube search results |
| 4 | **Search in browser** | `search for AI in chrome` | Opens search in Chrome specifically |
| 5 | **Search in new tab** | `search for React in new tab` | Opens search in a new browser tab |
| 6 | **Start conversational search** | `search` | `What should I search for?` (then type the query) |
| 7 | **Search in specific browser** | `search in brave` | `What should I search for?` (opens in Brave) |
| 8 | **Open a website** | `open github.com` | Opens the URL in default browser |
| 9 | **Open YouTube** | `open youtube` | Opens youtube.com |
| 10 | **Open + search YouTube** | `open youtube and search for Python` | Opens YouTube & searches |
| 11 | **Open + play YouTube** | `open youtube and play lofi beats` | Opens YouTube & plays the first result |
| 12 | **Play N-th video** | `play second` / `open 3` | Plays the 2nd/3rd video from last search results |
| 13 | **Open LeetCode** | `open leetcode` | Opens leetcode.com |

---

## 🖥️ Desktop — Apps & System

Available in **USER mode** and **PRIME mode** (unless noted).

### Opening Apps

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Open any app** | `open notepad` | `Opened notepad.` |
| 2 | **Open Chrome** | `open chrome` / `chrome` | Opens Google Chrome |
| 3 | **Open Edge** | `open edge` / `edge` | Opens Microsoft Edge |
| 4 | **Open Brave** | `open brave` / `brave` | Opens Brave Browser |
| 5 | **Open WhatsApp** | `open whatsapp` / `whatsapp` | Opens WhatsApp Desktop |
| 6 | **Open MS Store** | `open store` | Opens Microsoft Store |
| 7 | **Open by shortcut** | `open Calculator` | Searches Start Menu shortcuts and opens |
| 8 | **Open by file search** | `open myproject` | Searches Desktop/Downloads/Documents for a match |

### Closing Apps

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Close an app** | `close chrome` | Closes the Chrome window |
| 2 | **Close by name** | `close notepad` | Closes Notepad |

### Browser Tab Control

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Close specific tab** | `close youtube in chrome` | Cycles through Chrome tabs, closes the YouTube tab |
| 2 | **Close tab (alt)** | `close github tab` | Finds and closes the GitHub tab in any open browser |
| 3 | **Close tab in browser** | `close youtube tab in brave` | Closes YouTube tab specifically in Brave |
| 4 | **Open new tab** | `open new tab` | Opens a new tab in the active browser |
| 5 | **New tab in browser** | `open new tab in chrome` | Opens a new tab in Chrome specifically |
| 6 | **Close current tab** | `close tab` / `close this tab` | Closes the currently active browser tab |
| 7 | **Next tab** | `next tab` / `switch tab` | Switches to the next browser tab (Ctrl+Tab) |
| 8 | **Previous tab** | `previous tab` / `prev tab` | Switches to the previous browser tab (Ctrl+Shift+Tab) |

> **How it works:** MAX focuses the browser window, reads the window title (which reflects the active tab name), cycles through tabs using Ctrl+Tab until it finds a title containing the keyword, then closes it with Ctrl+W.

### Volume Control

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Mute** | `mute volume` | Mutes system audio |
| 2 | **Unmute** | `unmute volume` | Unmutes system audio |
| 3 | **Increase volume** | `increase volume` | Increases volume by 10% |
| 4 | **Decrease volume** | `decrease volume` | Decreases volume by 10% |
| 5 | **Set volume** | `set volume to 50` | Sets volume to 50% |

### System Actions

> ⚠️ Immediate actions (no delay) trigger a **YES/NO confirmation prompt**.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Shutdown** | `shut down` / `shutdown` | `Are you sure you want to shut down now? Say YES to confirm.` |
| 2 | **Restart** | `restart` / `reboot` | `Are you sure you want to restart now? Say YES to confirm.` |
| 3 | **Sleep** | `sleep` / `put to sleep` | `Are you sure you want to go to sleep now?` |
| 4 | **Lock screen** | `lock screen` / `lock my pc` | `Locking the screen...` (locks immediately) |
| 5 | **Unlock screen** | `unlock screen` | `Please enter your Windows PIN or password.` |

### Scheduled System Actions

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Shutdown after delay** | `shut down after 20 minutes` | `Got it. I will shut down in 20 minute(s).` |
| 2 | **Lock after delay** | `lock after 5 minutes` | `Got it. I will lock the screen in 5 minute(s).` |
| 3 | **Restart after delay** | `restart in 1 hour` | `Got it. I will restart in 60 minute(s).` |
| 4 | **Sleep after delay** | `sleep after 30 seconds` | `Got it. I will go to sleep in 30 second(s).` |
| 5 | **Timer notification** | `notify me after 10 seconds` | `I will notify you after 10 seconds.` |

---

## 📁 Files & Folders

Available in **USER mode**, except `delete` which requires **PRIME mode**.

### Creating Files & Folders

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Create text file** | `create text file report` | Creates `report.txt` in root |
| 2 | **Create file with ext** | `create file notes.md` | Creates `notes.md` |
| 3 | **Create file on Desktop** | `create file readme.txt on desktop` | Creates on Desktop |
| 4 | **Create folder** | `create folder Projects` | Creates `Projects/` in root |
| 5 | **Create folder on Desktop** | `create folder Work on desktop` | Creates on Desktop |

### Opening Files & Folders

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Open file by name** | `open report.txt` | Opens the file |
| 2 | **Open Downloads** | `open downloads` | Opens Downloads folder |
| 3 | **Open Desktop** | `open desktop` | Opens Desktop folder |
| 4 | **Open Documents** | `open documents` | Opens Documents folder |
| 5 | **Open on specific location** | `open project on desktop` | Opens from Desktop |

### Semantic / Date-Based File Open

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Yesterday's file** | `open yesterday's ppt` | Opens most recent `.pptx` modified yesterday |
| 2 | **Today's file** | `open today's document` | Opens newest `.docx` from today |
| 3 | **Latest file** | `open latest resume` | Opens newest resume/cv from last 30 days |
| 4 | **Recent file by type** | `open most recent pdf` | Opens newest PDF from last 30 days |
| 5 | **Last week's file** | `open last week's image` | Opens newest image from last 7 days |

### Deleting Files 🔴 PRIME MODE ONLY

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Delete file** | `delete old_report.txt` | `Are you sure you want to delete 'old_report.txt'? Say YES or NO.` |
| 2 | **Delete on location** | `delete draft on desktop` | Confirmation prompt → then deletes |

---

## 📝 Notes

Available in **USER mode** and **PRIME mode**.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Take a note** | `take a note buy groceries` | `Note saved.` |
| 2 | **Save note** | `save note meeting at 3pm` | `Note saved.` |
| 3 | **Add note** | `add note call dentist` | `Note saved.` |
| 4 | **Read notes** | `show my notes` / `read my notes` | Displays all saved notes |

---

## 🖥️ CDII — Cross-Desktop Control

Available in **USER mode** and **PRIME mode**.

> Requires `pyvda` (`pip install pyvda`) for virtual desktop features.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **List apps on desktop** | `what's running on Desktop 2` | Lists window titles on Desktop 2 |
| 2 | **Show apps** | `list apps on Desktop 1` | Lists window titles on Desktop 1 |
| 3 | **Pause app on desktop** | `pause YouTube on Desktop 3` | Sends pause to YouTube on Desktop 3 |
| 4 | **Play on desktop** | `play Spotify on Desktop 2` | Sends play to Spotify on Desktop 2 |
| 5 | **Close on desktop** | `close Chrome on Desktop 1` | Closes Chrome on Desktop 1 |
| 6 | **Mute on desktop** | `mute VLC on Desktop 2` | Sends mute to VLC on Desktop 2 |

---

## ⚡ Event-Based Automation

Available in **USER mode** and **PRIME mode**.

> Requires `psutil` (`pip install psutil`) for process monitoring.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Shutdown after video** | `shut down after this video ends` | `Watching media players. Will shutdown when video ends.` |
| 2 | **Lock after download** | `lock after download finishes` | `Watching Downloads folder. Will lock when download completes.` |
| 3 | **Notify on download** | `notify me when download finishes` | `Watching Downloads folder. Will notify when download completes.` |
| 4 | **Sleep after copy** | `sleep after copying completes` | `Watching for file copy completion.` |
| 5 | **Restart after video** | `restart after this video ends` | `Watching media players. Will restart when video ends.` |

---

## 🔗 Chained Automation

Available in **USER mode** and **PRIME mode**.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **And then** | `open chrome and then open notepad` | Runs both commands sequentially |
| 2 | **Then** | `open youtube then search for python` | Opens YouTube, then searches |
| 3 | **After that** | `open notepad after that open chrome` | Runs both sequentially |
| 4 | **Followed by** | `mute volume followed by lock screen` | Mutes then locks |

**Supported connectors:** `and then`, `then`, `after that`, `afterwards`, `followed by`

---

## 🎤 Voice Features

Available in **USER mode** and **PRIME mode**.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Enroll voice** | `enroll my voice` | Records 3 samples, saves speaker profile |
| 2 | **Train voice** | `train my voice` | Same as enroll |
| 3 | **Voice status** | `voice status` / `check voice` | Shows whether voice verification is active |

> After enrollment, all voice commands are verified against your profile.  
> Unrecognized voices are silently rejected.

---

## ⚙️ Configuration

Available in **USER mode** and **PRIME mode**.

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Set root path** | `set root C:\Projects` | `Root path set to 'C:\Projects'.` |

---

## 🚪 Session Control

| # | Command | Example | MAX Response |
|---|---------|---------|-------------|
| 1 | **Exit** | `exit` / `quit` / `bye` | `Shutting down MAX session.` |

---

## 🔒 Mode Comparison

| Feature | USER Mode | PRIME Mode |
|---------|:---------:|:----------:|
| Open apps / files / folders | ✅ | ✅ |
| Web search | ✅ | ✅ |
| Volume control | ✅ | ✅ |
| Take / read notes | ✅ | ✅ |
| Lock / Unlock screen | ✅ | ✅ |
| Scheduled actions (timed) | ✅ | ✅ |
| CDII cross-desktop | ✅ | ✅ |
| Event-based automation | ✅ | ✅ |
| Chained commands | ✅ | ✅ |
| Voice enrollment | ✅ | ✅ |
| **Delete files** | ❌ | ✅ |
| **Kill processes** | ❌ | ✅ |
| **Run shell commands** | ❌ | ✅ |
| **System shutdown** | ❌ | ✅ |

---

## 📍 Location Suffixes

Many file/folder commands support location suffixes:

| Suffix | Target Path |
|--------|------------|
| `on desktop` | `~/Desktop/` |
| `on downloads` / `in downloads` | `~/Downloads/` |
| `on documents` / `in documents` | `~/Documents/` |

**Example:** `create file report.txt on desktop` → Creates `report.txt` on Desktop.

---

## 🌊 Conversational Search Flow

MAX supports a conversational search mode:

```
you> search
MAX> What should I search for?
you> how to learn python
MAX> [Opens search results for "how to learn python"]
```

You can also cancel mid-flow:
```
you> search
MAX> What should I search for?
you> cancel
MAX> Search cancelled.
```

---

*Document generated for MAX Phase-1 MVP — All commands verified against codebase.*
