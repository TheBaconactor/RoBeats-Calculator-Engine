-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
v_u_1:update()
pcall(function() --[[ Line: 4 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v_u_2 = false
    local function _() --[[ Name: do_disable_coregui ]] --[[ Line: 6 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        local _, _ = pcall(function() --[[ Line: 7 ]]
            --[[ Upvalues: (ref 1): v_u_2 ]]
            local l_StarterGui_0 = game.StarterGui
            l_StarterGui_0:SetCore("TopbarEnabled", false)
            l_StarterGui_0:SetCore("ResetButtonCallback", false)
            l_StarterGui_0:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList, false)
            l_StarterGui_0:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)
            l_StarterGui_0:SetCoreGuiEnabled(Enum.CoreGuiType.Health, false)
            l_StarterGui_0:SetCoreGuiEnabled("Chat", false)
            l_StarterGui_0:SetCoreGuiEnabled(Enum.CoreGuiType.Chat, false)
            l_StarterGui_0:SetCoreGuiEnabled(Enum.CoreGuiType.All, false)
            v_u_2 = true
        end)
    end;
    local _, _ = pcall(function() --[[ Line: 7 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        local l_StarterGui_1 = game.StarterGui
        l_StarterGui_1:SetCore("TopbarEnabled", false)
        l_StarterGui_1:SetCore("ResetButtonCallback", false)
        l_StarterGui_1:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList, false)
        l_StarterGui_1:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)
        l_StarterGui_1:SetCoreGuiEnabled(Enum.CoreGuiType.Health, false)
        l_StarterGui_1:SetCoreGuiEnabled("Chat", false)
        l_StarterGui_1:SetCoreGuiEnabled(Enum.CoreGuiType.Chat, false)
        l_StarterGui_1:SetCoreGuiEnabled(Enum.CoreGuiType.All, false)
        v_u_2 = true
    end)
    spawn(function() --[[ Line: 25 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_1 ]]
        for v3 = 1, 15 do
            if v3 >= 10 and v_u_2 == true then
                break;
            end;
            local _, _ = pcall(function() --[[ Line: 7 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                local l_StarterGui_2 = game.StarterGui
                l_StarterGui_2:SetCore("TopbarEnabled", false)
                l_StarterGui_2:SetCore("ResetButtonCallback", false)
                l_StarterGui_2:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList, false)
                l_StarterGui_2:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)
                l_StarterGui_2:SetCoreGuiEnabled(Enum.CoreGuiType.Health, false)
                l_StarterGui_2:SetCoreGuiEnabled("Chat", false)
                l_StarterGui_2:SetCoreGuiEnabled(Enum.CoreGuiType.Chat, false)
                l_StarterGui_2:SetCoreGuiEnabled(Enum.CoreGuiType.All, false)
                v_u_2 = true
            end)
            v_u_1:wait(0.25)
        end;
    end)
end)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
v_u_4:set_as_client()
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v6 = require(game.ReplicatedStorage.Shared.ProdEnvSelector)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_7 = v6:client_wait_for_update((require(game.ReplicatedStorage.SDK.LoadAudioPrivateKey)))
local v_u_8 = require(game.ReplicatedStorage.Shared.EventString)
v_u_8:initialize_with_table_checksum(v_u_7)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
v_u_9:post_connect_update()
if v_u_1:is_dev_build() then
    v_u_4:puts("<DEV> Loading initial requires...")
end;
local v_u_10 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_11 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_12 = require(game.ReplicatedStorage.Local.ObjectPool)
local v_u_13 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_14 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_15 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_16 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_17 = require(game.ReplicatedStorage.Local.PlayerBlobManagerLocal)
local v_u_18 = require(game.ReplicatedStorage.Tutorial.TutorialManager)
local v_u_19 = require(game.ReplicatedStorage.SPChat.Local.SPChatLocal)
local v_u_20 = require(game.ReplicatedStorage.LocalShared.BGMManager)
local v_u_21 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_22 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v_u_23 = require(game.ReplicatedStorage.Local.GameJoin)
local v_u_24 = require(game.ReplicatedStorage.Lobby.LobbyJoin)
local v_u_25 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_26 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_27 = require(game.ReplicatedStorage.Shared.EnqueueFn)
local v_u_28 = require(game.ReplicatedStorage.LocalShared.ClientErrorReportManager)
local v_u_29 = require(game.ReplicatedStorage.LocalShared.ShopLocalProtocol)
local v_u_30 = require(game.ReplicatedStorage.LocalShared.AdornPool)
local v_u_31 = require(game.ReplicatedStorage.LocalShared.LocalPlayerSongStatsManager)
local v_u_32 = require(game.ReplicatedStorage.Shared.LuaPool)
local v_u_33 = require(game.ReplicatedStorage.LocalShared.PrePool)
local v_u_34 = require(game.ReplicatedStorage.LocalShared.PlayerSettingsManager)
local v_u_35 = require(game.ReplicatedStorage.LocalShared.LocalDanceClubManager)
local v_u_36 = require(game.ReplicatedStorage.LocalShared.IntersectZoneManager)
local v_u_37 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_38 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_39 = require(game.ReplicatedStorage.LocalShared.LocalPlayerStatusManager)
local v_u_40 = require(game.ReplicatedStorage.LocalShared.LocalGuildManager)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_41 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_42 = require(game.ReplicatedStorage.LocalShared.LocalLobbyFollowNPCManager)
local v43 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.GameStage.GameStageDatabase)
require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_44 = require(game.ReplicatedStorage.Tests.TestRunner)
local v45 = require(game.ReplicatedStorage.LocalShared.PlayerPolicy)
local v_u_46 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v_u_47 = require(game.ReplicatedStorage.Lobby.WebNPCLocalModelCache)
local v_u_48 = require(game.ReplicatedStorage.Pets.PetAssignmentInfo)
require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
if v_u_1:is_dev_build() then
    v_u_4:puts("<DEV> Loading Dependency requires...")
end;
require(game.ReplicatedStorage.Shared.Dependency):load_requires_client()
v43:client_startup()
v_u_21:hide_scripts()
v_u_21:hide_spremoteevent()
v45:client_init()
local function _(p49) --[[ Name: dev_build_startup_log ]] --[[ Line: 122 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_44 ]]
    if v_u_1:is_dev_build() then
        v_u_44:run_tests(p49)
    end;
end;
(function() --[[ Line: 128 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_8, (copy 4): v_u_21, (copy 5): v_u_14, (copy 6): v_u_7, (copy 7): v_u_5, (copy 8): v_u_25, (copy 9): v_u_26, (copy 10): v_u_13, (copy 11): v_u_11, (copy 12): v_u_12, (copy 13): v_u_16, (copy 14): v_u_27, (copy 15): v_u_30, (copy 16): v_u_32, (copy 17): v_u_34, (copy 18): v_u_36, (copy 19): v_u_47, (copy 20): v_u_46, (copy 21): v_u_20, (copy 22): v_u_28, (copy 23): v_u_23, (copy 24): v_u_24, (copy 25): v_u_29, (copy 26): v_u_31, (copy 27): v_u_17, (copy 28): v_u_18, (copy 29): v_u_19, (copy 30): v_u_35, (copy 31): v_u_39, (copy 32): v_u_40, (copy 33): v_u_42, (copy 34): v_u_33, (copy 35): v_u_22, (copy 36): v_u_15, (copy 37): v_u_10, (copy 38): v_u_38, (copy 39): v_u_37, (copy 40): v_u_41, (copy 41): v_u_44, (copy 42): v_u_9, (copy 43): v_u_48 ]]
    if v_u_1:is_dev_build() then
        v_u_4:puts("<DEV> LocalMain init started")
    end;
    v_u_1:wait()
    v_u_8:es_fn_enabled(true)
    v_u_21:initial_setup()
    local v50 = v_u_14:new({
        ["IsServer"] = false
    })
    v50:client_load_encodings_from_table(v_u_7)
    v_u_5:singleton():set_as_client(v50)
    if v_u_1:is_dev_build() then
        v_u_4:puts("<DEV> _local_services init")
    end;
    local v_u_51 = {
        ["_spui"] = v_u_25:new(5),
        ["_menus"] = v_u_26:new(),
        ["_game_join"] = nil,
        ["_lobby_join"] = nil,
        ["_input"] = v_u_13:new(),
        ["_sfx_manager"] = v_u_11:new(),
        ["_object_pool"] = v_u_12:new(),
        ["_evt"] = v50,
        ["_animation_manager"] = v_u_16:new(),
        ["_player_blob_manager"] = nil,
        ["_tutorial_manager"] = nil,
        ["_chat"] = nil,
        ["_bgm_manager"] = nil,
        ["_update_enqueue_fn"] = v_u_27:new(),
        ["_error_report"] = nil,
        ["_shop_local_protocol"] = nil,
        ["_adorn_pool"] = v_u_30:new(),
        ["_player_song_stats_manager"] = nil,
        ["_lua_pool"] = v_u_32:new(),
        ["_player_settings_manager"] = v_u_34:new(),
        ["_dance_club_manager"] = nil,
        ["_intersect_zone_manager"] = v_u_36:new(),
        ["_player_status_manager"] = nil,
        ["_guild_manager"] = nil,
        ["_follow_npc_manager"] = nil,
        ["_webnpc_local_model_cache"] = v_u_47:new()
    }
    v_u_21:set_local_services(v_u_51)
    v_u_46:init_singleton(v_u_51)
    v_u_51._bgm_manager = v_u_20:new(v_u_51)
    v_u_51._error_report = v_u_28:new(v_u_51)
    v_u_51._evt:set_error_report(v_u_51._error_report)
    v_u_51._game_join = v_u_23:new(v_u_51)
    v_u_51._lobby_join = v_u_24:new(v_u_51)
    v_u_51._shop_local_protocol = v_u_29:new(v_u_51, v_u_51._evt)
    v_u_51._player_song_stats_manager = v_u_31:new(v_u_51)
    v_u_51._player_blob_manager = v_u_17:new(v_u_51)
    v_u_51._tutorial_manager = v_u_18:new(v_u_51)
    v_u_51._chat = v_u_19:new(v_u_51)
    v_u_51._dance_club_manager = v_u_35:new(v_u_51)
    v_u_51._player_status_manager = v_u_39:new(v_u_51)
    v_u_51._guild_manager = v_u_40:new(v_u_51)
    v_u_51._follow_npc_manager = v_u_42:new(v_u_51)
    v_u_51._update_enqueue_fn:set_error_function(function(p52) --[[ Line: 195 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        v_u_51._error_report:report_client_error(p52)
    end)
    v_u_51.get_current_dayid = function(_) --[[ Name: get_current_dayid ]] --[[ Line: 199 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51._player_blob_manager:get_dayid();
    end;
    v_u_51.get_current_weekid = function(_) --[[ Name: get_current_weekid ]] --[[ Line: 200 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51._player_blob_manager:get_weekid();
    end;
    v_u_51.local_services_copy = function(_) --[[ Name: local_services_copy ]] --[[ Line: 201 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        local v53 = {}
        for v54, v55 in pairs(v_u_51) do
            v53[v54] = v55
        end;
        return v53;
    end;
    v_u_33:prepool(v_u_51)
    if v_u_1:is_dev_build() then
        v_u_4:puts("<DEV> init _local_services post")
    end;
    v_u_1:query_chat_status()
    v_u_51._player_blob_manager:do_sync()
    v_u_22:initial_setup(v_u_51)
    local v_u_56 = 0
    local v_u_57 = nil
    local v60 = game:GetService("RunService").Heartbeat:Connect(function(p58) --[[ Line: 222 ]]
        --[[ Upvalues: (ref 1): v_u_56, (ref 2): v_u_15, (ref 3): v_u_10, (ref 4): v_u_57, (ref 5): v_u_51, (ref 6): v_u_38, (ref 7): v_u_1 ]]
        v_u_56 = v_u_56 + p58
        local v59 = v_u_15:DeltaTimeToTimescale(p58)
        if v_u_56 > v_u_10.WAIT_SYNC_POPUP_TIME_SEC and v_u_57 == nil then
            v_u_57 = v_u_51._menus:push_menu(v_u_38:new(v_u_51, v_u_51._spui, v_u_51._menus):set_close_button_visible(false))
        end;
        if v_u_57 ~= nil then
            v_u_57:set_text("Attempting to connect to server...", string.format("The server may be down for maintenance. Try joining the game again, or re-trying at later time. Waiting for (%d) seconds.", (math.floor(v_u_56))))
        end;
        v_u_1:update()
        v_u_51._spui:layout()
        v_u_51._menus:update(v59, v_u_51)
        v_u_51._input:post_update()
    end)
    local v61 = v_u_57
    while v_u_51._player_blob_manager:is_synced() ~= true do
        v_u_1:wait(0.25)
    end;
    local v_u_62
    if v_u_1:is_dev_build() then
        v_u_4:puts("<DEV> query_chat_status")
        v_u_62 = v_u_51
    else
        v_u_62 = v_u_51
    end;
    while v_u_1:query_chat_status_finished() ~= true do
        v_u_1:wait(0.25)
    end;
    if v61 ~= nil then
        v_u_62._menus:remove_menu(v61)
        v_u_57 = nil
    end;
    v60:Disconnect()
    v_u_62._player_song_stats_manager:load_stats()
    if v_u_37:is_banned((v_u_62._player_blob_manager:get_player_blob())) ~= true then
        v_u_62._chat:init()
    end;
    if v_u_1:is_dev_build() then
        v_u_4:puts("<DEV> init post-sync")
    end;
    v_u_21:post_connect_setup(v_u_62)
    v_u_41:singleton():init_as_client(v_u_62)
    v_u_62._tutorial_manager:do_startup()
    if v_u_1:is_dev_build() then
        if v_u_1:is_dev_build() then
            v_u_44:run_tests(v_u_62)
        end;
    end;
    local function f_game_update(p63) --[[ Name: game_update ]] --[[ Line: 280 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_15, (ref 3): v_u_1, (ref 4): v_u_8, (ref 5): v_u_62, (ref 6): v_u_13, (ref 7): v_u_9, (ref 8): v_u_48, (ref 9): v_u_14, (ref 10): v_u_46, (ref 11): v_u_21, (ref 12): v_u_22 ]]
        v_u_4:set_as_client()
        local v_u_64 = v_u_15:DeltaTimeToTimescale(p63)
        local v70, v71 = v_u_1:try(function() --[[ Line: 285 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_62, (ref 3): v_u_13, (ref 4): v_u_1, (ref 5): v_u_4, (ref 6): v_u_9, (ref 7): v_u_48, (ref 8): v_u_14, (ref 9): v_u_46, (copy 10): v_u_64, (ref 11): v_u_21, (ref 12): v_u_22 ]]
            v_u_8:es_fn_enabled(true)
            if v_u_62._input:control_just_pressed(v_u_13.KEY_DEBUG_1) and v_u_62._menus:top_menu_swallows_input() == false then
                v_u_1.do_profile = not v_u_1.do_profile
                v_u_4:puts(string.format("Profiling(%s)", (tostring(v_u_1.do_profile))))
            end;
            if v_u_9.DebugLagButtonEnabled == true then
                if v_u_1:is_dev_build() and v_u_62._input:control_just_pressed(v_u_13.KEY_DEBUG_2) or v_u_9.DebugDoRandomLagButton and v_u_1:rand_rangei(0, 250) == 1 then
                    local v65
                    if v_u_1:rand_rangei(0, 4) == 1 then
                        v65 = v_u_1:rand_rangef(0.3, 0.5)
                    else
                        v65 = v_u_1:rand_rangef(0.01, 0.05)
                    end;
                    local v66 = tick()
                    local v67 = 0
                    while v65 >= tick() - v66 do
                        v67 = v67 + v_u_1:rand_rangei(0, 65536)
                    end;
                    v_u_4:warnf("Manual lag for (%.2f) seconds triggered", v65)
                end;
            elseif v_u_9.DebugSpamButtonEnabled == true and (v_u_1:is_dev_build() and v_u_62._input:control_just_pressed(v_u_13.KEY_DEBUG_2)) then
                v_u_4:warnf("Manual spam triggered")
                local v68 = v_u_62
                local v69 = v_u_48.AssignmentData:new(1, 1807)
                v69:get_pet_owned_id_set():add_set(12)
                for _ = 1, 10 do
                    v68._evt:fire_event_to_server(v_u_14.EVT_PetAssignment_SendAssignment_Client, v69:to_table())
                    v68._evt:fire_event_to_server(v_u_14.EVT_PetAssignment_CancelAssignment_Client, 1)
                end;
                v68._evt:fire_event_to_server(v_u_14.EVT_PetAssignment_SendAssignment_Client, v69:to_table())
            end;
            v_u_1:update()
            v_u_46:singleton():update(v_u_64)
            v_u_62._input:update(v_u_64)
            v_u_62._player_blob_manager:update(v_u_64)
            v_u_21:update(v_u_62, v_u_64)
            v_u_22:update(v_u_62, v_u_64)
            v_u_62._tutorial_manager:update(v_u_64)
            v_u_62._dance_club_manager:update(v_u_64)
            v_u_1:profilebegin("_chat:update")
            v_u_62._chat:update(v_u_64)
            v_u_1:profileend()
            v_u_1:profilebegin("_lobby_join:update")
            v_u_62._lobby_join:update(v_u_64)
            v_u_1:profileend()
            v_u_1:profilebegin("_game_join:update")
            v_u_62._game_join:update(v_u_64)
            v_u_1:profileend()
            v_u_46:singleton():update_post_camera_moved(v_u_64)
            v_u_62._bgm_manager:update(v_u_64)
            v_u_62._player_status_manager:update(v_u_64)
            v_u_62._player_song_stats_manager:update(v_u_64)
            v_u_62._guild_manager:update(v_u_64)
            v_u_1:profilebegin("_spui:layout")
            v_u_62._spui:layout()
            v_u_1:profileend()
            v_u_1:profilebegin("_menus:update")
            v_u_62._menus:update(v_u_64, v_u_62)
            v_u_1:profileend()
            v_u_1:profilebegin("_follow_npc_manager:update")
            v_u_62._follow_npc_manager:update(v_u_64)
            v_u_1:profileend()
            v_u_1:profilebegin("_game_join:post_update")
            v_u_62._game_join:post_update(v_u_64)
            v_u_1:profileend()
            v_u_1:profilebegin("_lobby_join:post_update")
            v_u_62._lobby_join:post_update(v_u_64)
            v_u_1:profileend()
            v_u_62._update_enqueue_fn:update(v_u_64)
            v_u_62._sfx_manager:update(v_u_64, v_u_62)
            v_u_62._input:post_update()
            v_u_46:singleton():post_update(v_u_64)
            v_u_22:post_update(v_u_62)
            if v_u_1.print_frame_gc == true then
                v_u_1:pop_gc_count()
            end;
        end)
        if not v70 then
            v_u_62._error_report:report_client_error(v71)
            v_u_62._input:set_frame_index_state(nil)
        end;
        v_u_8:es_fn_enabled(false)
    end;
    if v_u_1:is_dev_build() then
        v_u_4:puts("<DEV> init starting game thread")
    end;
    game:GetService("RunService").Heartbeat:Connect(function(p72) --[[ Line: 412 ]]
        --[[ Upvalues: (copy 1): f_game_update ]]
        f_game_update(p72)
    end)
    v_u_8:es_fn_enabled(false)
end)()
