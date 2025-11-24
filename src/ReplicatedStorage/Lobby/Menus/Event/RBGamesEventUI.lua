-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:49 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
require(game.ReplicatedStorage.Shared.GuildMessage)
require(game.ReplicatedStorage.Shared.GuildUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.RBGamesEventInfo)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
v9:require_client(function() --[[ Line: 34 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_12, (ref 4): v_u_13, (ref 5): v_u_14 ]]
    v_u_10 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.PreviewCharacterUI)
    v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
local v_u_54 = {
    ["show_tasks_menu"] = function(_, p15, p_u_16) --[[ Name: show_tasks_menu ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_2, (copy 3): v_u_6 ]]
        p15._menus:push_menu(v_u_12:new(p15, p15._spui, p15._menus, function(p17) --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_6, (copy 3): p_u_16 ]]
            p17:set_header_text(string.format("Tasks"))
            local v18 = v_u_2:new()
            for _, v19 in pairs(v_u_6.TaskFlags) do
                v18:push_back(v19)
            end;
            v18:remove_if(function(p20) --[[ Line: 56 ]]
                --[[ Upvalues: (ref 1): p_u_16 ]]
                return p_u_16:get_task_flag(p20);
            end)
            local v_u_21 = v_u_6:get_task_flag_to_point_amount()
            v18:sort(function(p22, p23) --[[ Line: 60 ]]
                --[[ Upvalues: (copy 1): v_u_21 ]]
                return v_u_21:get(p22) < v_u_21:get(p23);
            end)
            for _, v24 in v18:key_itr() do
                p17:get_element_list():push_back(v24)
            end;
        end, function(p25, p26, p27, _, p28) --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            p26.Text = v_u_6:get_task_flag_to_name():get(p25)
            p27.Image = "rbxassetid://18686397838"
            p28:get_description_display().Text = string.format("%d Points", v_u_6:get_task_flag_to_point_amount():get(p25))
            p28:set_select_button_enabled(false)
        end, function(_) end, function(_, _, _) end, game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.RBGamesListSelectUI:Clone())):get_list_adapter():set_do_wrap(true)
    end,
    ["show_hidden_items_menu"] = function(_, p29, p_u_30) --[[ Name: show_hidden_items_menu ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_6, (copy 3): v_u_1 ]]
        p29._menus:push_menu(v_u_12:new(p29, p29._spui, p29._menus, function(p31) --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            p31:set_header_text(string.format("Hidden Shines"))
            p31:get_element_list():push_back(v_u_6.ProgressFlags.Item1)
            p31:get_element_list():push_back(v_u_6.ProgressFlags.Item2)
            p31:get_element_list():push_back(v_u_6.ProgressFlags.Item3)
            p31:get_element_list():push_back(v_u_6.ProgressFlags.Item4)
            p31:get_element_list():push_back(v_u_6.ProgressFlags.Item5)
        end, function(p32, p33, p34, _, p35) --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_6, (copy 3): p_u_30 ]]
            p33.Text = v_u_1:string_replace(v_u_6:get_progress_flag_to_description():get(p32), ".", "")
            if p_u_30:get_progress_flag(p32) == true then
                p34.Image = "rbxassetid://18686471726"
                p35:get_description_display().Text = "Found!"
            else
                p34.Image = v_u_1:get_question_assetid()
                if p32 == v_u_6.ProgressFlags.Item1 then
                    p35:get_description_display().Text = "Behind the practice building!"
                elseif p32 == v_u_6.ProgressFlags.Item2 then
                    p35:get_description_display().Text = "Time for some STONKS!"
                elseif p32 == v_u_6.ProgressFlags.Item3 then
                    p35:get_description_display().Text = "Don\'t get run over by the subway!"
                elseif p32 == v_u_6.ProgressFlags.Item4 then
                    p35:get_description_display().Text = "Be a champion... someday!"
                elseif p32 == v_u_6.ProgressFlags.Item5 then
                    p35:get_description_display().Text = "Looking for team!"
                end;
            end;
            p35:set_select_button_enabled(false)
        end, function(_) end, function(_, _, _) end, game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.RBGamesListSelectUI:Clone()))
    end,
    ["show_settings_menu"] = function(_, p_u_36, _, p_u_37, p_u_38) --[[ Name: show_settings_menu ]] --[[ Line: 118 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_1, (ref 3): v_u_10, (copy 4): v_u_5 ]]
        p_u_36._menus:push_menu(v_u_12:new(p_u_36, p_u_36._spui, p_u_36._menus, function(p39) --[[ Line: 124 ]]
            p39:set_header_text(string.format("Settings"))
            p39:get_element_list():push_back(-1)
            p39:get_element_list():push_back(-2)
            p39:get_element_list():push_back(-3)
        end, function(p40, p41, p42, _, p43) --[[ Line: 130 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_37 ]]
            if p40 == -1 then
                p41.Text = "Songs Played (Server)"
                p42.Image = v_u_1:get_question_assetid()
                p43:get_description_display().Text = "Count: " .. tostring(p_u_37.SongCompleteCount)
                p43:set_select_button_enabled(false)
                return;
            elseif p40 == -2 then
                p41.Text = "Multiplayer Songs Played (Server)"
                p42.Image = v_u_1:get_question_assetid()
                p43:get_description_display().Text = "Count: " .. tostring(p_u_37.MultiplayerSongCompleteCount)
                p43:set_select_button_enabled(false)
            elseif p40 == -3 then
                p41.Text = "Reset Data"
                p42.Image = v_u_1:get_question_assetid()
                p43:get_description_display().Text = "Reset all event data."
                p43:set_select_button_text("Reset")
            end;
        end, function(p44) --[[ Line: 148 ]]
            --[[ Upvalues: (copy 1): p_u_36, (ref 2): v_u_10, (ref 3): v_u_5, (copy 4): p_u_38 ]]
            if p44 == -3 then
                p_u_36._menus:push_menu(v_u_10:new(p_u_36, p_u_36._spui, p_u_36._menus):set_text("Confirm", "Are you sure you want to reset your event data?")):set_okay_button_fn(function() --[[ Line: 152 ]]
                    --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_10, (ref 3): v_u_5, (ref 4): p_u_38 ]]
                    local v_u_45 = p_u_36._menus:push_menu(v_u_10:new(p_u_36, p_u_36._spui, p_u_36._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_36._evt:wait_on_event_once(v_u_5.EVT_SpecialEvent_RBGames_ResetData_Server, function() --[[ Line: 154 ]]
                        --[[ Upvalues: (ref 1): p_u_36, (copy 2): v_u_45, (ref 3): p_u_38, (ref 4): v_u_10 ]]
                        p_u_36._menus:remove_menu(v_u_45)
                        p_u_36._menus:remove_menu(p_u_38)
                        p_u_36._menus:push_menu(v_u_10:new(p_u_36, p_u_36._spui, p_u_36._menus):set_text("Data Reset", "Your event data has been reset."):set_close_button_visible(true))
                    end)
                    p_u_36._evt:fire_event_to_server(v_u_5.EVT_SpecialEvent_RBGames_ResetData_Client)
                end)
            end;
        end, function(_, _, _) end, game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.RBGamesListSelectUI:Clone()))
    end,
    ["do_claim_progress_flag"] = function(_, p_u_46, p47, p_u_48) --[[ Name: do_claim_progress_flag ]] --[[ Line: 167 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_6, (ref 3): v_u_10, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): v_u_8, (ref 7): v_u_14 ]]
        v_u_7:is_enum_member(p47, v_u_6.ProgressFlags)
        local v_u_49 = p_u_46._menus:push_menu(v_u_10:new(p_u_46, p_u_46._spui, p_u_46._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_46._evt:wait_on_event_once(v_u_5.EVT_SpecialEvent_RBGames_ClaimProgress_Server, function(p_u_50, p_u_51, p52) --[[ Line: 171 ]]
            --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_4, (ref 3): v_u_10, (copy 4): p_u_48, (ref 5): v_u_8, (copy 6): v_u_49, (ref 7): v_u_14 ]]
            local function f_finish() --[[ Name: finish ]] --[[ Line: 172 ]]
                --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_4, (ref 3): v_u_10, (copy 4): p_u_51, (ref 5): p_u_48, (copy 6): p_u_50 ]]
                p_u_46._sfx_manager:play_sfx(v_u_4.SFX_FANFARE)
                p_u_46._menus:push_menu(v_u_10:new(p_u_46, p_u_46._spui, p_u_46._menus):set_text("Claimed!", p_u_51):set_on_close_fn(function() --[[ Line: 174 ]]
                    --[[ Upvalues: (ref 1): p_u_48, (ref 2): p_u_50, (ref 3): p_u_51 ]]
                    if p_u_48 then
                        p_u_48(p_u_50, p_u_51)
                    end;
                end))
            end;
            local v_u_53 = v_u_8.RewardInfo:table_to_list(p52)
            if v_u_53:count() > 0 then
                p_u_46._player_blob_manager:do_sync(function() --[[ Line: 183 ]]
                    --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_49, (ref 3): v_u_14, (copy 4): v_u_53, (copy 5): f_finish ]]
                    p_u_46._menus:remove_menu(v_u_49)
                    p_u_46._menus:push_menu(v_u_14:new(p_u_46, p_u_46._spui, p_u_46._menus, v_u_53, function() --[[ Line: 186 ]]
                        --[[ Upvalues: (ref 1): f_finish ]]
                        f_finish()
                    end):set_header_text("Rewards"))
                end)
            else
                p_u_46._menus:remove_menu(v_u_49)
                f_finish()
            end;
        end)
        p_u_46._evt:fire_event_to_server(v_u_5.EVT_SpecialEvent_RBGames_ClaimProgress_Client, p47)
    end
}
v_u_54.show_menu = function(_, p_u_55) --[[ Name: show_menu ]] --[[ Line: 200 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_3, (ref 3): v_u_10, (copy 4): v_u_5, (copy 5): v_u_54, (ref 6): v_u_12, (copy 7): v_u_1 ]]
    if v_u_6:day_event_list_playerblob_is_event_active(p_u_55._player_blob_manager:get_day_event_list(), (p_u_55._player_blob_manager:get_player_blob())) ~= true then
        return v_u_3:warnf("RBGamesEventUI:show_menu() - Event not active.");
    end;
    (function(p_u_56) --[[ Name: get_player_progress_data ]] --[[ Line: 206 ]]
        --[[ Upvalues: (copy 1): p_u_55, (ref 2): v_u_10, (ref 3): v_u_5, (ref 4): v_u_6 ]]
        local v_u_57 = p_u_55._menus:push_menu(v_u_10:new(p_u_55, p_u_55._spui, p_u_55._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_55._evt:wait_on_event_once(v_u_5.EVT_SpecialEvent_RBGames_GetData_Server, function(p58, p59) --[[ Line: 208 ]]
            --[[ Upvalues: (ref 1): p_u_55, (copy 2): v_u_57, (copy 3): p_u_56, (ref 4): v_u_6 ]]
            p_u_55._menus:remove_menu(v_u_57)
            p_u_56(v_u_6.PlayerProgress:from_table(p58), p59)
        end)
        p_u_55._evt:fire_event_to_server(v_u_5.EVT_SpecialEvent_RBGames_GetData_Client)
    end)(function(p_u_60, p_u_61) --[[ Line: 215 ]]
        --[[ Upvalues: (copy 1): p_u_55, (ref 2): v_u_54, (ref 3): v_u_12, (ref 4): v_u_6, (ref 5): v_u_1 ]]
        local v_u_62 = nil
        local function _() --[[ Name: close_and_refresh_menu ]] --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): v_u_62, (ref 2): p_u_55, (ref 3): v_u_54 ]]
            if v_u_62 then
                p_u_55._menus:remove_menu(v_u_62)
            end;
            v_u_54:show_menu(p_u_55)
        end;
        local _ = p_u_55._menus:push_menu(v_u_12:new(p_u_55, p_u_55._spui, p_u_55._menus, function(p63) --[[ Line: 233 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_60 ]]
            p63:set_header_text(string.format("Event Menu"))
            p63:get_element_list():push_back(-1)
            p63:get_element_list():push_back(-2)
            p63:get_element_list():push_back(-3)
            p63:get_element_list():push_back(-4)
            p63:get_element_list():push_back(-5)
            p63:get_element_list():push_back(-6)
            if v_u_6:player_progress_can_claim_event_flag(p_u_60, v_u_6.ProgressFlags.CompleteAll) then
                p63:get_element_list():push_back(-7)
            end;
            if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Quest1) == true and (p_u_60:get_progress_flag(v_u_6.ProgressFlags.Quest2) == true and (p_u_60:get_progress_flag(v_u_6.ProgressFlags.Quest3) == true and p_u_60:get_progress_flag(v_u_6.ProgressFlags.CompleteAll) ~= true)) then
                p63:set_sub_text("Find all hidden shines, complete all missions and all tasks to earn a special RoBeats reward!")
            end;
        end, function(p64, p65, p66, _, p67) --[[ Line: 248 ]]
            --[[ Upvalues: (copy 1): p_u_60, (ref 2): v_u_6, (ref 3): v_u_1 ]]
            p66.ImageRectOffset = Vector2.new(0, 0)
            p66.ImageRectSize = Vector2.new(0, 0)
            local v68 = true
            if p64 == -1 then
                p65.Text = "Quest 1"
                p66.Image = "rbxassetid://18686471562"
                if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Quest1) == true then
                    p67:get_description_display().Text = "Mission Complete!"
                    p67:set_select_button_text("Claimed")
                else
                    p67:get_description_display().Text = v_u_6:get_progress_flag_to_description():get(v_u_6.ProgressFlags.Quest1)
                    p67:set_select_button_text("Claim")
                end;
                v68 = v_u_6:player_progress_can_claim_event_flag(p_u_60, v_u_6.ProgressFlags.Quest1)
            elseif p64 == -2 then
                p65.Text = "Quest 2"
                p66.Image = "rbxassetid://18686471562"
                if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Quest2) == true then
                    p67:get_description_display().Text = "Mission Complete!"
                    p67:set_select_button_text("Claimed")
                else
                    p67:get_description_display().Text = v_u_6:get_progress_flag_to_description():get(v_u_6.ProgressFlags.Quest2)
                    p67:set_select_button_text("Claim")
                end;
                v68 = v_u_6:player_progress_can_claim_event_flag(p_u_60, v_u_6.ProgressFlags.Quest2)
            elseif p64 == -3 then
                p65.Text = "Quest 3"
                p66.Image = "rbxassetid://18686471562"
                if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Quest3) == true then
                    p67:get_description_display().Text = "Mission Complete!"
                    p67:set_select_button_text("Claimed")
                else
                    p67:get_description_display().Text = v_u_6:get_progress_flag_to_description():get(v_u_6.ProgressFlags.Quest3)
                    p67:set_select_button_text("Claim")
                end;
                v68 = v_u_6:player_progress_can_claim_event_flag(p_u_60, v_u_6.ProgressFlags.Quest3)
            elseif p64 == -4 then
                p65.Text = string.format("Tasks (Points: %d)", p_u_60:calculate_task_points())
                p66.Image = "rbxassetid://18686397838"
                p67:get_description_display().Text = "Complete tasks to earn points!"
                p67:set_select_button_text("View")
            elseif p64 == -5 then
                p65.Text = "Hidden Shines"
                p66.Image = "rbxassetid://18686471726"
                local v69 = 5
                if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Item1) == true then
                    v69 = v69 - 1
                end;
                if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Item2) == true then
                    v69 = v69 - 1
                end;
                if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Item3) == true then
                    v69 = v69 - 1
                end;
                if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Item4) == true then
                    v69 = v69 - 1
                end;
                if p_u_60:get_progress_flag(v_u_6.ProgressFlags.Item5) == true then
                    v69 = v69 - 1
                end;
                if v69 > 0 then
                    p67:get_description_display().Text = string.format("%d remaining Hidden Shine(s)!", v69)
                else
                    p67:get_description_display().Text = "You found all the hidden shines!"
                end;
                p67:set_select_button_text("View")
            elseif p64 == -6 then
                p65.Text = "Settings"
                p66.Image = v_u_1:gear_assetid()
                p67:get_description_display().Text = ""
                p67:set_select_button_text("View")
            elseif p64 == -7 then
                p65.Text = "Completed Everything!"
                p66.Image = "rbxassetid://18686397838"
                p67:get_description_display().Text = "Completed everything... Here\'s your special reward!"
                p67:set_select_button_text("Claim")
                v68 = v_u_6:player_progress_can_claim_event_flag(p_u_60, v_u_6.ProgressFlags.CompleteAll)
            end;
            p67:set_select_button_enabled(v68)
        end, function(p70) --[[ Line: 331 ]]
            --[[ Upvalues: (ref 1): v_u_54, (ref 2): p_u_55, (ref 3): v_u_6, (ref 4): v_u_62, (copy 5): p_u_60, (copy 6): p_u_61 ]]
            if p70 == -1 then
                v_u_54:do_claim_progress_flag(p_u_55, v_u_6.ProgressFlags.Quest1, function() --[[ Line: 333 ]]
                    --[[ Upvalues: (ref 1): v_u_62, (ref 2): p_u_55, (ref 3): v_u_54 ]]
                    if v_u_62 then
                        p_u_55._menus:remove_menu(v_u_62)
                    end;
                    v_u_54:show_menu(p_u_55)
                end)
                return;
            elseif p70 == -2 then
                v_u_54:do_claim_progress_flag(p_u_55, v_u_6.ProgressFlags.Quest2, function() --[[ Line: 335 ]]
                    --[[ Upvalues: (ref 1): v_u_62, (ref 2): p_u_55, (ref 3): v_u_54 ]]
                    if v_u_62 then
                        p_u_55._menus:remove_menu(v_u_62)
                    end;
                    v_u_54:show_menu(p_u_55)
                end)
                return;
            elseif p70 == -3 then
                v_u_54:do_claim_progress_flag(p_u_55, v_u_6.ProgressFlags.Quest3, function() --[[ Line: 337 ]]
                    --[[ Upvalues: (ref 1): v_u_62, (ref 2): p_u_55, (ref 3): v_u_54 ]]
                    if v_u_62 then
                        p_u_55._menus:remove_menu(v_u_62)
                    end;
                    v_u_54:show_menu(p_u_55)
                end)
                return;
            elseif p70 == -4 then
                v_u_54:show_tasks_menu(p_u_55, p_u_60)
                return;
            elseif p70 == -5 then
                v_u_54:show_hidden_items_menu(p_u_55, p_u_60)
                return;
            elseif p70 == -6 then
                v_u_54:show_settings_menu(p_u_55, p_u_60, p_u_61, v_u_62)
            elseif p70 == -7 then
                v_u_54:do_claim_progress_flag(p_u_55, v_u_6.ProgressFlags.CompleteAll, function() --[[ Line: 345 ]]
                    --[[ Upvalues: (ref 1): v_u_62, (ref 2): p_u_55, (ref 3): v_u_54 ]]
                    if v_u_62 then
                        p_u_55._menus:remove_menu(v_u_62)
                    end;
                    v_u_54:show_menu(p_u_55)
                end)
            end;
        end, function(_, _, _) end, game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.RBGamesListSelectUI:Clone()):set_close_on_element_select(false))
    end)
end;
return v_u_54;
