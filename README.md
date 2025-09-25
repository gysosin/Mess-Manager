# ??? File Organizer: Because Your Downloads Folder is a Dumpster Fire ??

*Congratulations, your digital life is a mess. This tool is here to judge you and fix it.* ????

It auto-sorts your chaotic file hoarding into folders so neat, you'll cry. CLI for terminal wannabe-hackers ?? and Web UI for people who think "command line" is a pickup line ???.

## ? Features (AKA "Stuff You're Too Lazy to Do Yourself")

- ?? **Dual Mode**: CLI for try-hards, Web UI for the rest of you mortals
- ?? **Minimal Setup**: CLI works out of the box; `pip install -r requirements.txt` adds the web UI + AI sauce
- ?? **"Genius" Organization**: File extensions with a superiority complex
- ?? **Folder Selection**: Wow, you can organize other trash heaps besides Downloads
- ? **Daily Scheduling**: For when you're too busy downloading cat memes to care
- ??? **Safe Operation**: Won't nuke your files... unless you deserve it
- ?? **Obsessive Logging**: Proof of how much of a disaster you are
- ?? **AI Assist (optional)**: Let OpenAI, Perplexity, or Mistral judge your files when extensions give up
- 💬 **Chat UI**: Because clicking buttons is apparently too hard for you
- 🎯 **Smart Subfolders**: AI reads your pathetic file names and creates folders like "Pictures/Vacation" for your 47 identical sunset pics
- 🧮 **Vector Database**: Remembers every file you've ever hoarded so you can ask "how many memes did I download?"
- 🔍 **Query System**: Chat with your file history like it's ChatGPT, but more judgemental

## ?? File Categories (Because You Need Labels for Your Chaos)

- ??? **Pictures**: jpg, png, gif, svg, avif *(Your 47 identical sunset pics)*
- ?? **Video**: mp4, avi, mkv, mov *(Totally not pirated Linux ISOs, right?)*
- ?? **Music**: mp3, wav, flac, aac *(Your "ironic" 90s playlist)*
- ?? **Documents**: pdf, doc, txt, xls, ppt *(Files you'll never open again)*
- ??? **Compressed**: zip, rar, 7z, tar, iso *(Inception-level archives)*
- ?? **Programs**: exe, msi, deb, dmg *(Hope that's not a virus)*
- ?? **Code**: py, js, html, css, java *(Your half-baked "apps")*
- ?? **Others**: The digital equivalent of "I'll deal with it later"

## ?? Usage Options (Choose Your Shame)

### ?? CLI Mode (For "I Use Arch BTW" Nerds)
*No frills unless you ask for AI*

```bash
# Organize Downloads (it's always Downloads, isn't it?)
python file_organizer.py

# Organize your other digital landfills
python file_organizer.py --folder "C:/Users/you/Hoard"
python file_organizer.py -f "D:/WhyDoIHaveThis"

# Ask the robots for help (fallback mode only touches unknown stuff)
python file_organizer.py --ai-provider openai --ai-scope fallback

# Go full Skynet and let AI override the rules
python file_organizer.py --ai-provider mistral --ai-scope always --ai-model mistral-large-latest

# Beg for help (we get it)
python file_organizer.py --help
```

### ?? Web UI Mode (For People Who Fear Terminals)
*Clicky-clicky for the faint of heart*

```bash
# One-time setup (yes, it's *that* painful)
pip install -r requirements.txt

# Witness the magic
python file_organizer.py --web

# Be extra with custom ports
python file_organizer.py --web --port 8080

# Avoid human interaction
python file_organizer.py --web --no-browser
```

Flip the "Enable AI-assisted categorization" toggle in the UI, pick your provider, paste an API key (it never gets saved), and let the bots clean up.

## ?? AI Setup (Summon the Robots)

1. Install optional deps: `pip install -r requirements.txt`
2. Set an API key (or pass `--ai-api-key` on the CLI):
   ```powershell
   setx OPENAI_API_KEY "sk-your-openai-key"
   setx PERPLEXITY_API_KEY "pplx-your-perplexity-key"
   setx MISTRAL_API_KEY "mst-your-mistral-key"
   ```
3. Pick your vibe:
   - `fallback` scope calls AI only when the built-in rules shrug
   - `always` scope lets AI overrule extension-based guesses
4. Optional knobs: `--ai-model`, `--ai-timeout` (seconds)

You can mix providers between CLI runs. The web UI toggle remembers the last choice for the session.

## ?? Setup Instructions (Don't Screw This Up)

### 1?? Schedule Daily Execution (Because You'll Forget)
Run as Administrator *(Windows is clingy, ugh)*:
```bash
setup_scheduler.bat
```

Sets a task for 9:00 AM daily. Perfect for cleaning up your nightly meme binges ??

### 2?? Customize Schedule (Because You Don't Do Mornings)
- Open Windows Task Scheduler ??
- Hunt for "FileOrganizerDaily" ??
- Reschedule for when you're actually awake ?

## ?? Logs (Your Digital Walk of Shame)
Check `Downloads/file_organizer_logs/` for a detailed record of your file crimes ??

## ??? Safety Features (Because You're a Walking Disaster)
- ? Only moves files, never deletes *(We're not that cruel)*
- ?? Ignores hidden files *(Your shady secrets are safe)*
- ?? Handles duplicates *(Because you download "funny_cat.jpg" 12 times)*
- ?? Creates folders *(Like a snarky digital maid)*

---

*Built with ?? and enough sarcasm to drown your poorly named files* ??
