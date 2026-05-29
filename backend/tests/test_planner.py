from neuronos.planner import Planner


def test_music_request_creates_open_and_search_steps():
    plan = Planner().build_plan("Open Brave and search lo-fi music")

    assert plan.summary == "Open Brave and search for lo-fi music."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.search"]
    assert plan.steps[0].requires_approval is False
    assert plan.steps[1].args["query"] == "lo-fi music"


def test_memory_request_creates_memory_write_step():
    plan = Planner().build_plan(
        "Remember that my LangGraph project is in D:\\Projects\\langgraph"
    )

    assert plan.summary == "Save this preference or project note to memory."
    assert [step.tool for step in plan.steps] == ["memory.write"]
    assert "LangGraph project" in plan.steps[0].args["content"]


def test_unknown_request_returns_conversation_step():
    plan = Planner().build_plan("What should I work on today?")

    assert plan.steps[0].tool == "conversation.respond"
    assert plan.steps[0].requires_approval is False


def test_youtube_song_request_uses_youtube_playback_tool():
    plan = Planner().build_plan("open brave and then in it open youtube and play faded song")

    assert plan.summary == "Open Brave and play Faded on YouTube."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.play_youtube"]
    assert plan.steps[1].args["query"] == "faded song"


def test_global_warming_video_request_uses_youtube_playback_tool():
    plan = Planner().build_plan("Open Brave and Open YouTube and play a video on global warming.")

    assert plan.summary == "Open Brave and play Global Warming on YouTube."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.play_youtube"]
    assert plan.steps[1].args["query"] == "global warming"


def test_misheard_brave_youtube_video_request_uses_youtube_playback_tool():
    plan = Planner().build_plan("Open the raise and open YouTube and video on global warming.")

    assert plan.summary == "Open Brave and play Global Warming on YouTube."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.play_youtube"]
    assert plan.steps[1].args["query"] == "global warming"


def test_open_vscode_request_launches_vscode():
    plan = Planner().build_plan("open vs code")

    assert plan.summary == "Open VS Code."
    assert [step.tool for step in plan.steps] == ["app.launch"]
    assert plan.steps[0].args["app"] == "VS Code"


def test_open_folder_in_vscode_creates_folder_step():
    plan = Planner().build_plan(r"open D:\Games\ui in vscode")

    assert plan.summary == r"Open D:\Games\ui in VS Code."
    assert [step.tool for step in plan.steps] == ["app.open_path"]
    assert plan.steps[0].args["app"] == "VS Code"
    assert plan.steps[0].args["path"] == r"D:\Games\ui"


def test_open_file_explorer_request_launches_explorer():
    plan = Planner().build_plan("open file explorer")

    assert plan.summary == "Open File Explorer."
    assert [step.tool for step in plan.steps] == ["app.launch"]
    assert plan.steps[0].args["app"] == "File Explorer"


def test_open_calculator_request_launches_generic_app():
    plan = Planner().build_plan("open calculator")

    assert plan.summary == "Open Calculator."
    assert [step.tool for step in plan.steps] == ["app.launch"]
    assert plan.steps[0].args["app"] == "Calculator"


def test_open_discard_request_launches_discord():
    plan = Planner().build_plan("Open discard.")

    assert plan.summary == "Open Discord."
    assert [step.tool for step in plan.steps] == ["app.launch"]
    assert plan.steps[0].args["app"] == "Discord"


def test_polite_open_settings_request_launches_settings():
    plan = Planner().build_plan("Can you open settings?")

    assert plan.summary == "Open Settings."
    assert [step.tool for step in plan.steps] == ["app.launch"]
    assert plan.steps[0].args["app"] == "Settings"


def test_open_brave_and_chatgpt_request_opens_chatgpt_directly():
    plan = Planner().build_plan("open brave and search chatgpt and open it")

    assert plan.summary == "Open Brave and open ChatGPT."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["browser"] == "Brave"
    assert plan.steps[1].args["url"] == "https://chatgpt.com"


def test_known_site_open_defaults_to_brave_without_saying_brave():
    plan = Planner().build_plan("i want to open chatgpt")

    assert plan.summary == "Open Brave and open ChatGPT."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[0].args == {"app": "Brave"}
    assert plan.steps[1].args == {"browser": "Brave", "url": "https://chatgpt.com"}


def test_open_gmail_defaults_to_brave_instead_of_fake_app():
    plan = Planner().build_plan("open gmail")

    assert plan.summary == "Open Brave and open Gmail."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://gmail.com"


def test_youtube_play_defaults_to_brave_without_saying_brave():
    plan = Planner().build_plan("play faded on youtube")

    assert plan.summary == "Open Brave and play Faded on YouTube."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.play_youtube"]
    assert plan.steps[1].args == {"browser": "Brave", "query": "faded"}


def test_plain_search_defaults_to_brave():
    plan = Planner().build_plan("search local ai news")

    assert plan.summary == "Open Brave and search for local ai news."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.search"]
    assert plan.steps[1].args == {"browser": "Brave", "query": "local ai news"}


def test_open_brave_and_misheard_chatgpt_request_opens_chatgpt_directly():
    plan = Planner().build_plan("Open brave and then open chagibity in it and ask what is the weather today.")

    assert plan.summary == "Open Brave and open ChatGPT."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://chatgpt.com"


def test_open_brave_and_chat_gpp_request_opens_chatgpt_directly():
    plan = Planner().build_plan("Open brave and search chat GPP and open it.")

    assert plan.summary == "Open Brave and open ChatGPT."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://chatgpt.com"


def test_open_raf_and_charge_equity_request_opens_chatgpt_directly():
    plan = Planner().build_plan("Open the RAF, then search charge equity and open it.")

    assert plan.summary == "Open Brave and open ChatGPT."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://chatgpt.com"


def test_open_brave_and_google_cloud_request_opens_google_cloud_directly():
    plan = Planner().build_plan("Open Brave and Search Google Cloud and Open Hit.")

    assert plan.summary == "Open Brave and open Google Cloud."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://cloud.google.com"


def test_open_brave_and_perplexity_request_opens_perplexity_directly():
    plan = Planner().build_plan("Open brave and search perplexity and open it.")

    assert plan.summary == "Open Brave and open Perplexity."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://perplexity.ai"


def test_open_brave_and_linkedin_jobs_request_opens_directly():
    plan = Planner().build_plan("Open brave and search linkedin jobs and open it.")

    assert plan.summary == "Open Brave and open LinkedIn Jobs."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://linkedin.com/jobs"


def test_open_brave_and_hacker_news_request_opens_directly():
    plan = Planner().build_plan("Open brave and search hacker news and open it.")

    assert plan.summary == "Open Brave and open Hacker News."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://news.ycombinator.com"


def test_open_brave_and_open_gmail_opens_gmail_directly():
    plan = Planner().build_plan("open brave and open gmail")

    assert plan.summary == "Open Brave and open Gmail."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.open_url"]
    assert plan.steps[1].args["url"] == "https://gmail.com"


def test_compound_open_brave_and_ask_request_does_not_become_fake_app_name():
    plan = Planner().build_plan("open brave and ask what is the weather today")

    assert [step.tool for step in plan.steps] == ["conversation.respond"]


def test_open_brave_and_ask_about_drive_space_does_not_false_positive_to_google_drive():
    plan = Planner().build_plan("Open brave and ask about my drive space.")

    assert [step.tool for step in plan.steps] == ["conversation.respond"]


def test_open_brave_and_search_team_chat_stays_as_search_not_teams_site():
    plan = Planner().build_plan("Open brave and search team chat.")

    assert plan.summary == "Open Brave and search for team chat."
    assert [step.tool for step in plan.steps] == ["app.launch", "browser.search"]
    assert plan.steps[1].args["query"] == "team chat"


def test_volume_control_requests_route_to_system_audio():
    planner = Planner()

    lower_plan = planner.build_plan("reduce the volume")
    increase_plan = planner.build_plan("increase volume")
    turn_up_plan = planner.build_plan("turn volume up")
    mute_plan = planner.build_plan("mute the volume")
    unmute_plan = planner.build_plan("unmute volume")
    set_plan = planner.build_plan("set volume to 35")
    increase_to_plan = planner.build_plan("increase volume to 64")
    raise_to_plan = planner.build_plan("raise the volume to 64")
    clamped_set_plan = planner.build_plan("set volume to 150")
    lower_clamped_set_plan = planner.build_plan("set volume to -5")

    assert [step.tool for step in lower_plan.steps] == ["system.audio"]
    assert lower_plan.steps[0].args == {"direction": "down", "amount": 10}

    assert [step.tool for step in increase_plan.steps] == ["system.audio"]
    assert increase_plan.steps[0].args == {"direction": "up", "amount": 10}

    assert [step.tool for step in turn_up_plan.steps] == ["system.audio"]
    assert turn_up_plan.steps[0].args == {"direction": "up", "amount": 10}

    assert [step.tool for step in mute_plan.steps] == ["system.audio"]
    assert mute_plan.steps[0].args == {"direction": "mute", "amount": 10}

    assert [step.tool for step in unmute_plan.steps] == ["system.audio"]
    assert unmute_plan.steps[0].args == {"direction": "unmute", "amount": 10}

    assert [step.tool for step in set_plan.steps] == ["system.audio"]
    assert set_plan.steps[0].args == {"direction": "set", "amount": 35}

    assert [step.tool for step in increase_to_plan.steps] == ["system.audio"]
    assert increase_to_plan.steps[0].args == {"direction": "set", "amount": 64}

    assert [step.tool for step in raise_to_plan.steps] == ["system.audio"]
    assert raise_to_plan.steps[0].args == {"direction": "set", "amount": 64}

    assert [step.tool for step in clamped_set_plan.steps] == ["system.audio"]
    assert clamped_set_plan.steps[0].args == {"direction": "set", "amount": 100}

    assert [step.tool for step in lower_clamped_set_plan.steps] == ["system.audio"]
    assert lower_clamped_set_plan.steps[0].args == {"direction": "set", "amount": 0}


def test_settings_requests_route_to_system_settings_with_normalized_pages():
    planner = Planner()

    bluetooth_plan = planner.build_plan("open bluetooth settings")
    wifi_plan = planner.build_plan("open wi-fi settings")
    display_plan = planner.build_plan("open display settings")
    sound_plan = planner.build_plan("open sound settings")
    apps_plan = planner.build_plan("open apps settings")
    power_plan = planner.build_plan("open power settings")

    assert bluetooth_plan.steps[0].tool == "system.settings"
    assert bluetooth_plan.steps[0].args == {"page": "bluetooth"}

    assert wifi_plan.steps[0].tool == "system.settings"
    assert wifi_plan.steps[0].args == {"page": "wifi"}

    assert display_plan.steps[0].tool == "system.settings"
    assert display_plan.steps[0].args == {"page": "display"}

    assert sound_plan.steps[0].tool == "system.settings"
    assert sound_plan.steps[0].args == {"page": "sound"}

    assert apps_plan.steps[0].tool == "system.settings"
    assert apps_plan.steps[0].args == {"page": "apps"}

    assert power_plan.steps[0].tool == "system.settings"
    assert power_plan.steps[0].args == {"page": "power"}


def test_network_toggle_requests_route_to_system_network():
    planner = Planner()

    wifi_on_plan = planner.build_plan("turn wi-fi on")
    wifi_off_plan = planner.build_plan("turn wifi off")
    bluetooth_on_plan = planner.build_plan("turn bluetooth on")
    bluetooth_off_plan = planner.build_plan("turn bluetooth off")

    assert wifi_on_plan.steps[0].tool == "system.network"
    assert wifi_on_plan.steps[0].args == {"kind": "wifi", "enabled": True}

    assert wifi_off_plan.steps[0].tool == "system.network"
    assert wifi_off_plan.steps[0].args == {"kind": "wifi", "enabled": False}

    assert bluetooth_on_plan.steps[0].tool == "system.network"
    assert bluetooth_on_plan.steps[0].args == {"kind": "bluetooth", "enabled": True}

    assert bluetooth_off_plan.steps[0].tool == "system.network"
    assert bluetooth_off_plan.steps[0].args == {"kind": "bluetooth", "enabled": False}


def test_brightness_requests_route_to_system_brightness():
    planner = Planner()

    set_plan = planner.build_plan("set brightness to 70")
    high_plan = planner.build_plan("set brightness to 150")
    low_plan = planner.build_plan("set brightness to -5")

    assert set_plan.steps[0].tool == "system.brightness"
    assert set_plan.steps[0].args == {"percent": 70}

    assert high_plan.steps[0].tool == "system.brightness"
    assert high_plan.steps[0].args == {"percent": 100}

    assert low_plan.steps[0].tool == "system.brightness"
    assert low_plan.steps[0].args == {"percent": 0}


def test_simple_brightness_phrases_route_to_system_brightness():
    increase_plan = Planner().build_plan("increase brightness")
    lower_plan = Planner().build_plan("lower brightness")

    assert increase_plan.steps[0].tool == "system.brightness"
    assert increase_plan.steps[0].args == {"percent": 70}

    assert lower_plan.steps[0].tool == "system.brightness"
    assert lower_plan.steps[0].args == {"percent": 30}


def test_power_requests_route_to_system_power_and_require_shutdown_approval():
    planner = Planner()

    restart_plan = planner.build_plan("restart the pc")
    sleep_plan = planner.build_plan("sleep the pc")
    lock_plan = planner.build_plan("lock the pc")
    shutdown_plan = planner.build_plan("shut down the pc")

    assert restart_plan.steps[0].tool == "system.power"
    assert restart_plan.steps[0].args == {"action": "restart"}
    assert restart_plan.steps[0].requires_approval is False

    assert sleep_plan.steps[0].tool == "system.power"
    assert sleep_plan.steps[0].args == {"action": "sleep"}
    assert sleep_plan.steps[0].requires_approval is False

    assert lock_plan.steps[0].tool == "system.power"
    assert lock_plan.steps[0].args == {"action": "lock"}
    assert lock_plan.steps[0].requires_approval is False

    assert shutdown_plan.steps[0].tool == "system.power"
    assert shutdown_plan.steps[0].args == {"action": "shutdown"}
    assert shutdown_plan.steps[0].requires_approval is True


def test_default_folder_requests_route_to_app_open_default():
    planner = Planner()

    downloads_plan = planner.build_plan("open downloads")
    documents_plan = planner.build_plan("open documents")
    desktop_plan = planner.build_plan("open desktop")

    assert downloads_plan.steps[0].tool == "app.open_default"
    assert downloads_plan.steps[0].args == {"path": r"%USERPROFILE%\Downloads"}

    assert documents_plan.steps[0].tool == "app.open_default"
    assert documents_plan.steps[0].args == {"path": r"%USERPROFILE%\Documents"}

    assert desktop_plan.steps[0].tool == "app.open_default"
    assert desktop_plan.steps[0].args == {"path": r"%USERPROFILE%\Desktop"}


def test_bare_mute_routes_to_system_audio():
    plan = Planner().build_plan("mute")

    assert [step.tool for step in plan.steps] == ["system.audio"]
    assert plan.steps[0].args == {"direction": "mute", "amount": 10}


def test_bare_unmute_routes_to_system_audio():
    plan = Planner().build_plan("unmute")

    assert [step.tool for step in plan.steps] == ["system.audio"]
    assert plan.steps[0].args == {"direction": "unmute", "amount": 10}


def test_mute_the_laptop_routes_to_system_audio():
    plan = Planner().build_plan("mute the laptop")

    assert [step.tool for step in plan.steps] == ["system.audio"]
    assert plan.steps[0].args == {"direction": "mute", "amount": 10}


def test_lower_the_sound_routes_to_system_audio():
    plan = Planner().build_plan("lower the sound")

    assert [step.tool for step in plan.steps] == ["system.audio"]
    assert plan.steps[0].args == {"direction": "down", "amount": 10}


def test_open_settings_and_go_to_bluetooth_routes_to_system_settings():
    plan = Planner().build_plan("open settings and go to bluetooth")

    assert [step.tool for step in plan.steps] == ["system.settings"]
    assert plan.steps[0].args == {"page": "bluetooth"}


def test_restart_my_laptop_routes_to_system_power():
    plan = Planner().build_plan("restart my laptop")

    assert [step.tool for step in plan.steps] == ["system.power"]
    assert plan.steps[0].args == {"action": "restart"}
    assert plan.steps[0].requires_approval is False


def test_open_downloads_folder_routes_to_app_open_default():
    plan = Planner().build_plan("open downloads folder")

    assert [step.tool for step in plan.steps] == ["app.open_default"]
    assert plan.steps[0].args == {"path": r"%USERPROFILE%\Downloads"}


def test_polite_open_bluetooth_settings_routes_to_system_settings():
    plan = Planner().build_plan("Can you open bluetooth settings?")

    assert [step.tool for step in plan.steps] == ["system.settings"]
    assert plan.steps[0].args == {"page": "bluetooth"}


def test_polite_open_settings_and_go_to_bluetooth_routes_to_system_settings():
    plan = Planner().build_plan("Can you open settings and go to bluetooth?")

    assert [step.tool for step in plan.steps] == ["system.settings"]
    assert plan.steps[0].args == {"page": "bluetooth"}


def test_polite_open_downloads_folder_routes_to_app_open_default():
    plan = Planner().build_plan("Please open downloads folder")

    assert [step.tool for step in plan.steps] == ["app.open_default"]
    assert plan.steps[0].args == {"path": r"%USERPROFILE%\Downloads"}


def test_polite_restart_my_laptop_routes_to_system_power():
    plan = Planner().build_plan("Please restart my laptop")

    assert [step.tool for step in plan.steps] == ["system.power"]
    assert plan.steps[0].args == {"action": "restart"}
    assert plan.steps[0].requires_approval is False


def test_polite_shutdown_pc_routes_to_system_power_with_approval():
    plan = Planner().build_plan("Please shut down the pc")

    assert [step.tool for step in plan.steps] == ["system.power"]
    assert plan.steps[0].args == {"action": "shutdown"}
    assert plan.steps[0].requires_approval is True


def test_polite_run_command_routes_to_terminal_run_with_approval():
    plan = Planner().build_plan("Can you run dir?")

    assert [step.tool for step in plan.steps] == ["terminal.run"]
    assert plan.steps[0].args == {"command": "dir"}
    assert plan.steps[0].requires_approval is True
