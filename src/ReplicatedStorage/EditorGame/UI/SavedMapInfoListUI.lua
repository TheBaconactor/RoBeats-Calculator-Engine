-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:11 PM
-- Time elapsed: 21 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
local v_u_9 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
local v_u_14 = require(game.ReplicatedStorage.EditorGame.Data.EditorGamePlayInfo)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
local v_u_21 = nil
local v_u_22 = nil
local v_u_23 = nil
v15:require_client(function() --[[ Line: 37 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18, (ref 4): v_u_19, (ref 5): v_u_20, (ref 6): v_u_21, (ref 7): v_u_22, (ref 8): v_u_23 ]]
    v_u_16 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_19 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI)
    v_u_20 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.SongSelectV3UI)
    v_u_22 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI_Util)
    v_u_23 = require(game.ReplicatedStorage.EditorGame.Game.CustomMapPreviewUI)
end)
local v_u_42 = {
    ["message_box_confirm"] = function(_, p24, p_u_25, p26, p27) --[[ Name: message_box_confirm ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        p24._menus:push_menu(v_u_16:new(p24, p24._spui, p24._menus):set_text(p26 == nil and "Confirm" or p26, p27 == nil and "Are you sure you want to exit?" or p27):set_okay_button_fn(function() --[[ Line: 53 ]]
            --[[ Upvalues: (copy 1): p_u_25 ]]
            p_u_25()
        end))
    end,
    ["get_editor_menu_restore_menu_name"] = function(_) --[[ Name: get_editor_menu_restore_menu_name ]] --[[ Line: 315 ]]
        return "SavedMapInfoListUI:show_editor_menu";
    end,
    ["get_saved_map_info_list_select_ui_params"] = function(_) --[[ Name: get_saved_map_info_list_select_ui_params ]] --[[ Line: 477 ]]
        return {
            ["ListElementProto"] = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Editor.ListSelectUI_ListElement_SavedMapInfo:Clone()
        };
    end,
    ["list_select_ui_apply_settings"] = function(_, p28) --[[ Name: list_select_ui_apply_settings ]] --[[ Line: 483 ]]
        p28:set_close_on_element_select(false)
        p28:set_refresh_on_refocus(true)
        p28:get_list_adapter():set_do_wrap(true)
    end,
    ["list_element_render_saved_map_info"] = function(_, p_u_29, p_u_30) --[[ Name: list_element_render_saved_map_info ]] --[[ Line: 489 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_8 ]]
        v_u_1:ptry(function() --[[ Line: 490 ]]
            --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_1, (copy 3): p_u_30, (ref 4): v_u_8 ]]
            local l_PlayerIcon_0 = p_u_29:get_ui_root().PlayerIcon
            l_PlayerIcon_0.Image = v_u_1:transparent_assetid()
            v_u_1:get_user_thumbnail(p_u_30:get_creator_rbxid(), function(p31, _) --[[ Line: 493 ]]
                --[[ Upvalues: (copy 1): l_PlayerIcon_0 ]]
                if l_PlayerIcon_0 ~= nil then
                    l_PlayerIcon_0.Image = p31
                end;
            end, false)
            p_u_29:get_ui_root().SongIcon.Image = v_u_8:singleton():get_coverimage_assetid_for_key(p_u_30:get_source_songkey())
            local l_Display_0 = p_u_29:get_ui_root().DifficultyDisplaySection.Display
            l_Display_0.Text = p_u_30:get_assigned_difficulty_string()
            if p_u_30:has_assigned_difficulty() then
                l_Display_0.TextColor3 = v_u_8:singleton():get_difficulty_color_for_difficulty(p_u_30:get_assigned_difficulty())
            else
                l_Display_0.TextColor3 = v_u_8:singleton():get_difficulty_color_for_difficulty(10)
            end;
            local l_LikeDisplay_0 = p_u_29:get_ui_root().LikeDisplay
            if p_u_30:get_like_count() > 0 then
                l_LikeDisplay_0.Text = string.format("\240\159\145\141 %d", p_u_30:get_like_count())
            else
                l_LikeDisplay_0.Text = "-"
            end;
        end)
    end,
    ["show_creator_data_ui"] = function(_, p_u_32) --[[ Name: show_creator_data_ui ]] --[[ Line: 686 ]]
        --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_6, (copy 3): v_u_9, (ref 4): v_u_18, (copy 5): v_u_1 ]]
        local v_u_33 = v_u_16:loading_menu(p_u_32)
        p_u_32._evt:wait_on_event_once(v_u_6.EVT_Editor_GetCreatorData_Server, function(p34) --[[ Line: 688 ]]
            --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_32, (copy 3): v_u_33, (ref 4): v_u_9, (ref 5): v_u_18, (ref 6): v_u_1 ]]
            v_u_16:remove_loading_menu(p_u_32, v_u_33)
            local v_u_35 = v_u_9.CreatorData:from_table(p34)
            p_u_32._menus:push_menu(v_u_18:new(p_u_32, p_u_32._spui, p_u_32._menus, function(p36) --[[ Line: 698 ]]
                p36:set_header_text("Creator Data")
                p36:get_element_list():push_back(1)
            end, function(p37, p38, p39, _, p40) --[[ Line: 702 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_35 ]]
                if p37 == 1 then
                    p38.Text = "Recieved Likes (On your Custom Maps)"
                    p39.Image = v_u_1:thumbs_up_assetid()
                    p40:set_select_button_enabled(false)
                    p40:get_description_display().Text = string.format("\240\159\145\141 %d", v_u_35:get_received_like_count())
                end;
            end, function(p41) --[[ Line: 710 ]]
                if p41 ~= nil then
                end;
            end)):set_close_on_element_select(false)
        end)
        p_u_32._evt:fire_event_to_server(v_u_6.EVT_Editor_GetCreatorData_Client, v_u_1:get_local_userid())
    end
}
local function f_load_player_recent_saved_map_info_list(p_u_43, p_u_44) --[[ Name: load_player_recent_saved_map_info_list ]] --[[ Line: 58 ]]
    --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_6, (copy 3): v_u_9 ]]
    local v_u_45 = p_u_43._menus:push_menu(v_u_16:new(p_u_43, p_u_43._spui, p_u_43._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_43._evt:wait_on_event_once(v_u_6.EVT_Editor_GetPlayerRecent_Server, function(p46) --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): p_u_43, (copy 2): v_u_45, (copy 3): p_u_44, (ref 4): v_u_9 ]]
        p_u_43._menus:remove_menu(v_u_45)
        p_u_44(v_u_9.SavedMapInfo:info_list_from_table(p46))
    end)
    p_u_43._evt:fire_event_to_server(v_u_6.EVT_Editor_GetPlayerRecent_Client)
end;
local function f_load_custom_map_data_key(p_u_47, p48, p_u_49) --[[ Name: load_custom_map_data_key ]] --[[ Line: 67 ]]
    --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_6, (copy 3): v_u_9 ]]
    local v_u_50 = p_u_47._menus:push_menu(v_u_16:new(p_u_47, p_u_47._spui, p_u_47._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_47._evt:wait_on_event_once(v_u_6.EVT_Editor_LoadCustomMap_Server, function(p51, p52, p53, p54) --[[ Line: 69 ]]
        --[[ Upvalues: (copy 1): p_u_47, (copy 2): v_u_50, (copy 3): p_u_49, (ref 4): v_u_9 ]]
        p_u_47._menus:remove_menu(v_u_50)
        p_u_49(p51, v_u_9.CustomMapData:from_table(p52), v_u_9.SavedMapInfo:from_table(p53), v_u_9.LoadCustomMapAdditionalInfo:from_table(p54))
    end)
    p_u_47._evt:fire_event_to_server(v_u_6.EVT_Editor_LoadCustomMap_Client, p48)
end;
local function _(p_u_55, p_u_56) --[[ Name: try_play_custom_map_data_key ]] --[[ Line: 81 ]]
    --[[ Upvalues: (copy 1): f_load_custom_map_data_key, (ref 2): v_u_16, (copy 3): v_u_5, (ref 4): v_u_23, (copy 5): v_u_14 ]]
    f_load_custom_map_data_key(p_u_55, p_u_56, function(p57, p_u_58, p_u_59, p_u_60) --[[ Line: 82 ]]
        --[[ Upvalues: (copy 1): p_u_55, (ref 2): v_u_16, (copy 3): p_u_56, (ref 4): v_u_5, (ref 5): v_u_23, (ref 6): v_u_14 ]]
        if p57 ~= true then
            return p_u_55._menus:push_menu(v_u_16:new(p_u_55, p_u_55._spui, p_u_55._menus):set_text("Error", string.format("Failed to load custom map data for key \'%s\'.", p_u_56)));
        end;
        local v_u_61 = p_u_55._lobby_join:get_lobby()
        if v_u_61 == nil then
            return v_u_5:warnf("SavedMapInfoListUI:show_load_map_code_ui() - lobby is nil");
        end;
        v_u_23:create_custom_map_preview_ui(p_u_55, p_u_59, p_u_58, p_u_60, function() --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_60, (copy 3): v_u_61, (copy 4): p_u_59, (copy 5): p_u_58 ]]
            local v62 = v_u_14:new()
            v62:set_rewarded_play(true)
            v62:set_load_custom_map_additional_info(p_u_60)
            v_u_61._spectate_manager:start_editor_custom_map_game(p_u_59, p_u_58, v62)
        end)
    end)
end;
v_u_42.show_load_map_code_ui = function(_, p_u_63) --[[ Name: show_load_map_code_ui ]] --[[ Line: 102 ]]
    --[[ Upvalues: (copy 1): f_load_custom_map_data_key, (ref 2): v_u_16, (copy 3): v_u_5, (ref 4): v_u_23, (copy 5): v_u_14, (ref 6): v_u_20 ]]
    local function _(p_u_64) --[[ Name: on_text_input ]] --[[ Line: 103 ]]
        --[[ Upvalues: (copy 1): p_u_63, (ref 2): f_load_custom_map_data_key, (ref 3): v_u_16, (ref 4): v_u_5, (ref 5): v_u_23, (ref 6): v_u_14 ]]
        if #p_u_64 == 0 then
            return;
        elseif #p_u_64 <= 50 then
            local v_u_65 = p_u_63
            f_load_custom_map_data_key(v_u_65, p_u_64, function(p66, p_u_67, p_u_68, p_u_69) --[[ Line: 82 ]]
                --[[ Upvalues: (copy 1): v_u_65, (ref 2): v_u_16, (copy 3): p_u_64, (ref 4): v_u_5, (ref 5): v_u_23, (ref 6): v_u_14 ]]
                if p66 ~= true then
                    return v_u_65._menus:push_menu(v_u_16:new(v_u_65, v_u_65._spui, v_u_65._menus):set_text("Error", string.format("Failed to load custom map data for key \'%s\'.", p_u_64)));
                end;
                local v_u_70 = v_u_65._lobby_join:get_lobby()
                if v_u_70 == nil then
                    return v_u_5:warnf("SavedMapInfoListUI:show_load_map_code_ui() - lobby is nil");
                end;
                v_u_23:create_custom_map_preview_ui(v_u_65, p_u_68, p_u_67, p_u_69, function() --[[ Line: 93 ]]
                    --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_69, (copy 3): v_u_70, (copy 4): p_u_68, (copy 5): p_u_67 ]]
                    local v71 = v_u_14:new()
                    v71:set_rewarded_play(true)
                    v71:set_load_custom_map_additional_info(p_u_69)
                    v_u_70._spectate_manager:start_editor_custom_map_game(p_u_68, p_u_67, v71)
                end)
            end)
        end;
    end;
    p_u_63._menus:push_menu(v_u_20:new(p_u_63):eval(function(p_u_72) --[[ Line: 115 ]]
        --[[ Upvalues: (copy 1): p_u_63, (ref 2): f_load_custom_map_data_key, (ref 3): v_u_16, (ref 4): v_u_5, (ref 5): v_u_23, (ref 6): v_u_14 ]]
        p_u_72:get_title_display().Text = "Enter Map Code"
        p_u_72:get_sub_text_display().Text = "Enter map code - this should be in the format of \'name@1234@56\'."
        p_u_72:get_text_box().Text = ""
        p_u_72:get_text_box().TextSize = 32
        p_u_72:set_max_length(50)
        p_u_72:select_all_text_box()
        p_u_72:set_okay_button_fn(function() --[[ Line: 124 ]]
            --[[ Upvalues: (copy 1): p_u_72, (ref 2): p_u_63, (ref 3): f_load_custom_map_data_key, (ref 4): v_u_16, (ref 5): v_u_5, (ref 6): v_u_23, (ref 7): v_u_14 ]]
            local l_Text_0 = p_u_72:get_text_box().Text
            if #l_Text_0 == 0 then
                return;
            elseif #l_Text_0 <= 50 then
                local v_u_73 = p_u_63
                f_load_custom_map_data_key(v_u_73, l_Text_0, function(p74, p_u_75, p_u_76, p_u_77) --[[ Line: 82 ]]
                    --[[ Upvalues: (copy 1): v_u_73, (ref 2): v_u_16, (copy 3): l_Text_0, (ref 4): v_u_5, (ref 5): v_u_23, (ref 6): v_u_14 ]]
                    if p74 ~= true then
                        return v_u_73._menus:push_menu(v_u_16:new(v_u_73, v_u_73._spui, v_u_73._menus):set_text("Error", string.format("Failed to load custom map data for key \'%s\'.", l_Text_0)));
                    end;
                    local v_u_78 = v_u_73._lobby_join:get_lobby()
                    if v_u_78 == nil then
                        return v_u_5:warnf("SavedMapInfoListUI:show_load_map_code_ui() - lobby is nil");
                    end;
                    v_u_23:create_custom_map_preview_ui(v_u_73, p_u_76, p_u_75, p_u_77, function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_77, (copy 3): v_u_78, (copy 4): p_u_76, (copy 5): p_u_75 ]]
                        local v79 = v_u_14:new()
                        v79:set_rewarded_play(true)
                        v79:set_load_custom_map_additional_info(p_u_77)
                        v_u_78._spectate_manager:start_editor_custom_map_game(p_u_76, p_u_75, v79)
                    end)
                end)
            end;
        end)
        p_u_72:set_text_box_empty_text("name@1234@56")
    end))
end;
v_u_42.show_player_recent_maps_ui = function(_, p_u_80) --[[ Name: show_player_recent_maps_ui ]] --[[ Line: 134 ]]
    --[[ Upvalues: (copy 1): f_load_player_recent_saved_map_info_list, (ref 2): v_u_18, (copy 3): v_u_8, (copy 4): v_u_42, (copy 5): v_u_1, (copy 6): f_load_custom_map_data_key, (ref 7): v_u_16, (ref 8): v_u_19, (copy 9): v_u_9, (copy 10): v_u_3, (copy 11): v_u_4 ]]
    f_load_player_recent_saved_map_info_list(p_u_80, function(p_u_81) --[[ Line: 135 ]]
        --[[ Upvalues: (copy 1): p_u_80, (ref 2): v_u_18, (ref 3): v_u_8, (ref 4): v_u_42, (ref 5): v_u_1, (ref 6): f_load_custom_map_data_key, (ref 7): v_u_16, (ref 8): v_u_19, (ref 9): v_u_9, (ref 10): v_u_3, (ref 11): v_u_4 ]]
        p_u_80._menus:remove_menu_if(function(p82) --[[ Line: 138 ]]
            return p82.__type_key == "SavedMapInfoListUI:show_player_recent_maps_ui";
        end)
        local v93 = p_u_80._menus:push_menu(v_u_18:new(p_u_80, p_u_80._spui, p_u_80._menus, function(p83) --[[ Line: 146 ]]
            --[[ Upvalues: (copy 1): p_u_81, (ref 2): v_u_8 ]]
            p83:set_header_text("Your Saved Maps")
            for v84 = 1, p_u_81:count() do
                if v_u_8:singleton():contains_key(p_u_81:get(v84):get_source_songkey()) == true then
                    p83:get_element_list():push_front(p_u_81:get(v84))
                end;
            end;
        end, function(p85, p86, _, _, p87) --[[ Line: 153 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_1, (ref 3): v_u_8 ]]
            if #p85:get_custom_map_name() == 0 then
                p86.Text = "<EMPTY>"
            else
                p86.Text = p85:get_custom_map_name()
            end;
            v_u_42:list_element_render_saved_map_info(p87, p85)
            p87:set_select_button_enabled(true)
            p87:set_select_button_text("Open")
            p87:get_description_display().Text = string.format("Saved: %s - Song: %s", os.date(nil, p85:get_last_edit_time()), v_u_1:string_sub_max_len(v_u_8:singleton():get_title_for_key(p85:get_source_songkey()), 32))
        end, function(p_u_88) --[[ Line: 169 ]]
            --[[ Upvalues: (ref 1): f_load_custom_map_data_key, (ref 2): p_u_80, (ref 3): v_u_16, (ref 4): v_u_19 ]]
            if p_u_88 ~= nil then
                f_load_custom_map_data_key(p_u_80, p_u_88:get_custom_map_data_key(), function(p89, p90, p91, _) --[[ Line: 171 ]]
                    --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_16, (copy 3): p_u_88, (ref 4): v_u_19 ]]
                    if p89 ~= true then
                        return p_u_80._menus:push_menu(v_u_16:new(p_u_80, p_u_80._spui, p_u_80._menus):set_text("Error", string.format("Failed to load custom map data for key \'%s\'", p_u_88:get_custom_map_data_key())));
                    end;
                    p_u_80._menus:push_menu(v_u_19:new(p_u_80, p91, p90):load_custom_map_note_data())
                end)
            end;
        end, function(p92) --[[ Line: 184 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            p92:set_sub_text(string.format("Maps: %d / %d", p92:get_element_list():count(), v_u_9.SavedMapInfo:get_max_recent_saved_map_info_count()))
        end, nil, v_u_42:get_saved_map_info_list_select_ui_params()))
        v_u_42:list_select_ui_apply_settings(v93)
        v93.__type_key = "SavedMapInfoListUI:show_player_recent_maps_ui"
        local v94 = v_u_3:new()
        v94:push_back(function(p95) --[[ Line: 201 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_42, (ref 3): p_u_80 ]]
            v_u_4:set_button_text(p95, "\226\158\149 Create Map")
            p95:bind_data(function() --[[ Line: 203 ]]
                --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_80 ]]
                v_u_42:select_from_available_songkeys(p_u_80, function(p96) --[[ Line: 204 ]]
                    --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_80 ]]
                    v_u_42:create_new_map_for_song_key(p_u_80, p96)
                end)
            end)
        end)
        v_u_18:set_filter_button_fns_list(v93, v94)
    end)
end;
local function f_editor_song_select_test_songkey_filter(p97) --[[ Name: editor_song_select_test_songkey_filter ]] --[[ Line: 214 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    local v98 = v_u_8:singleton():key_get_audiomod(p97)
    local v99 = v_u_8:singleton():get_songkey_priority(p97)
    local v100 = v_u_8:singleton():key_is_remix_flagged(p97)
    local v101
    if v98 == v_u_8.MOD_NORMAL and v99 ~= v_u_8.SongPriority.Hidden then
        v101 = v100 == false
    else
        v101 = false
    end;
    return v101;
end;
v_u_42.can_show_editor_menu_for_songkey = function(_, p102) --[[ Name: can_show_editor_menu_for_songkey ]] --[[ Line: 221 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): f_editor_song_select_test_songkey_filter ]]
    local v103 = true
    local v104 = v_u_8:singleton():get_audiomod_to_modes_of_songkey(p102)
    if v104:contains(v_u_8.MOD_NORMAL) ~= true then
        return false;
    end;
    if f_editor_song_select_test_songkey_filter((v104:get(v_u_8.MOD_NORMAL))) ~= true then
        v103 = false
    end;
    return v103;
end;
v_u_42.test_can_local_player_create_new_map_for_song = function(_, p105, p106) --[[ Name: test_can_local_player_create_new_map_for_song ]] --[[ Line: 235 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_11, (copy 3): v_u_10, (copy 4): v_u_42 ]]
    local v107 = v_u_8:singleton():get_audiomod_to_modes_of_songkey(p106)
    local v108 = v_u_11:playerblob_has_access_to_song(p105._player_blob_manager:get_player_blob(), v107:get(v_u_8.MOD_HARDMODE), p105:get_current_dayid(), p105._player_blob_manager:get_cached_collection_info()) and true or (v_u_11:playerblob_has_access_to_song(p105._player_blob_manager:get_player_blob(), p106, p105:get_current_dayid(), p105._player_blob_manager:get_cached_collection_info()) and true or v107:contains(v_u_8.MOD_EASY) == true)
    local v109, v110 = v_u_10:is_event_active(p105._player_blob_manager:get_day_event_list())
    local v111 = v109 and v_u_10:get_playable_song_set(v110):contains(p106) and true or v108
    if v111 == true and v_u_42:can_show_editor_menu_for_songkey(p106) ~= true then
        v111 = false
    end;
    return v111;
end;
local v_u_112 = nil
v_u_42.select_from_available_songkeys = function(_, p_u_113, p_u_114) --[[ Name: select_from_available_songkeys ]] --[[ Line: 281 ]]
    --[[ Upvalues: (ref 1): v_u_112, (ref 2): v_u_21, (copy 3): v_u_8, (copy 4): v_u_10 ]]
    if v_u_112 == nil then
        v_u_112 = v_u_21:create_info_state()
    end;
    local v124 = v_u_21:new(p_u_113, v_u_112, function(p115) --[[ Line: 289 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        local v116 = v_u_8:singleton():get_songkey_priority(p115)
        local v117 = v_u_8:singleton():key_is_remix_flagged(p115)
        local v118
        if v116 == v_u_8.SongPriority.Hidden then
            v118 = false
        else
            v118 = v117 == false
        end;
        return v118;
    end, function(p119) --[[ Line: 294 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_114 ]]
        if v_u_8:singleton():contains_key(p119) then
            p_u_114(v_u_8:singleton():get_audiomod_to_modes_of_songkey(p119):get(v_u_8.MOD_NORMAL))
        end;
    end, function(p120) --[[ Line: 300 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_113, (ref 3): v_u_8 ]]
        local v121, v122 = v_u_10:is_event_active(p_u_113._player_blob_manager:get_day_event_list())
        if v121 then
            for v123, _ in v_u_10:get_playable_song_set(v122):key_itr() do
                if v_u_8:singleton():key_get_audiomod(v123) == v_u_8.MOD_NORMAL then
                    p120:add_set(v123)
                end;
            end;
        end;
    end)
    v124.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 311 ]]
        return "DebugEditorSongSelectRestoreKey";
    end;
    p_u_113._menus:push_menu(v124)
end;
v_u_42.create_new_map_for_song_key = function(_, p125, p126) --[[ Name: create_new_map_for_song_key ]] --[[ Line: 317 ]]
    --[[ Upvalues: (copy 1): v_u_42, (ref 2): v_u_16, (copy 3): v_u_9, (copy 4): v_u_1, (ref 5): v_u_19 ]]
    if v_u_42:test_can_local_player_create_new_map_for_song(p125, p126) ~= true then
        return p125._menus:push_menu(v_u_16:new(p125, p125._spui, p125._menus):set_text("Error", "You do not have access to create a map for this song."));
    end;
    local v127 = v_u_9.CustomMapData:new()
    local v128 = v_u_9.SavedMapInfo:new()
    v128:set_source_songkey(p126)
    v128:set_creator_rbxid(v_u_1:get_local_userid())
    v128:set_creator_name(v_u_1:get_local_username())
    v128:set_last_edit_time(os.time())
    p125._menus:push_menu(v_u_19:new(p125, v128, v127):load_songdatabase_note_data())
end;
v_u_42.show_editor_menu = function(_, p_u_129) --[[ Name: show_editor_menu ]] --[[ Line: 336 ]]
    --[[ Upvalues: (copy 1): v_u_42, (ref 2): v_u_18, (copy 3): v_u_10, (copy 4): v_u_1, (copy 5): v_u_9, (copy 6): v_u_5 ]]
    v_u_42:move_camera_to_editor_position(p_u_129)
    local v130 = v_u_42:get_editor_menu_restore_menu_name()
    local v142 = p_u_129._menus:push_menu(v_u_18:new(p_u_129, p_u_129._spui, p_u_129._menus, function(p131) --[[ Line: 353 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_129 ]]
        p131:set_header_text("Map Editor")
        p131:set_sub_text("")
        p131:get_element_list():push_back(0)
        p131:get_element_list():push_back(1)
        p131:get_element_list():push_back(2)
        p131:get_element_list():push_back(3)
        p131:get_element_list():push_back(4)
        local v132, _ = v_u_10:is_event_active(p_u_129._player_blob_manager:get_day_event_list())
        if v132 then
            p131:get_element_list():push_back(5)
        end;
        p131:get_element_list():push_back(6)
        p131:get_element_list():push_back(7)
    end, function(p133, p134, p135, _, p136) --[[ Line: 368 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        if p133 == 0 then
            p134.Text = "Create New Map"
            p135.Image = v_u_1:get_iconhd_crafting()
            p136:set_select_button_enabled(true)
            p136:get_description_display().Text = "Create a new map from any owned or event song."
            return;
        elseif p133 == 1 then
            p134.Text = "Load Your Saved Map"
            p135.Image = v_u_1:get_song_icon()
            p136:set_select_button_enabled(true)
            p136:get_description_display().Text = "Load a saved map."
            return;
        elseif p133 == 2 then
            p134.Text = "Play Map Code"
            p135.Image = v_u_1:get_hud_button_chat_assetid()
            p136:set_select_button_enabled(true)
            p136:get_description_display().Text = "Enter a map code to play."
            return;
        elseif p133 == 3 then
            p134.Text = "View Latest Published Maps"
            p135.Image = v_u_1:get_iconhd_trophy()
            p136:set_select_button_enabled(true)
            p136:get_description_display().Text = "View all latest published maps."
            return;
        elseif p133 == 4 then
            p134.Text = "View Published Maps for Song"
            p135.Image = v_u_1:get_iconhd_trophy()
            p136:set_select_button_enabled(true)
            p136:get_description_display().Text = "View latest published maps for song."
            return;
        elseif p133 == 5 then
            p134.Text = "View Published Maps for Event"
            p135.Image = v_u_1:get_iconhd_trophy()
            p136:set_select_button_enabled(true)
            p136:get_description_display().Text = "View latest published maps for the current event."
            return;
        elseif p133 == 6 then
            p134.Text = "View Your Liked Maps"
            p135.Image = v_u_1:thumbs_up_assetid()
            p136:set_select_button_enabled(true)
            p136:get_description_display().Text = "View published maps you have liked."
        elseif p133 == 7 then
            p134.Text = "View Your Creator Data"
            p135.Image = v_u_1:important_assetid()
            p136:set_select_button_enabled(true)
            p136:get_description_display().Text = "View your custom map creator stats."
        end;
    end, function(p137) --[[ Line: 420 ]]
        --[[ Upvalues: (ref 1): v_u_42, (copy 2): p_u_129, (ref 3): v_u_9, (ref 4): v_u_5 ]]
        if p137 == nil then
            return;
        elseif p137 == 0 then
            v_u_42:select_from_available_songkeys(p_u_129, function(p138) --[[ Line: 423 ]]
                --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_129 ]]
                v_u_42:create_new_map_for_song_key(p_u_129, p138)
            end)
            return;
        elseif p137 == 1 then
            v_u_42:show_player_recent_maps_ui(p_u_129)
            return;
        elseif p137 == 2 then
            v_u_42:show_load_map_code_ui(p_u_129)
            return;
        elseif p137 == 3 then
            v_u_42:show_published_map_list_ui(p_u_129, v_u_9.PublishCategory.Global, 0, function(p139) --[[ Line: 434 ]]
                p139:set_sub_text("Latest Published Maps")
            end)
            return;
        elseif p137 == 4 then
            v_u_42:select_from_available_songkeys(p_u_129, function(p140) --[[ Line: 439 ]]
                --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_129 ]]
                v_u_42:show_published_map_list_ui_for_songkey(p_u_129, p140)
            end)
            return;
        elseif p137 == 5 then
            v_u_42:show_published_map_list_ui_for_artist_event(p_u_129)
            return;
        elseif p137 == 6 then
            v_u_42:show_published_map_list_ui(p_u_129, v_u_9.PublishCategory.MyLikedMaps, 0, function(p141) --[[ Line: 447 ]]
                p141:set_header_text("Your Liked Maps")
            end)
            return;
        elseif p137 == 7 then
            v_u_42:show_creator_data_ui(p_u_129)
        else
            v_u_5:warnf("SavedMapInfoListUI:show_editor_menu() - unknown option %d", p137)
        end;
    end)):set_close_on_element_select(false):set_refresh_on_refocus(true):set_do_not_update_while_camera_transitioning(true)
    v142.__type_key = v130
    v142.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 465 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        return v_u_42:get_editor_menu_restore_menu_name();
    end;
end;
local function f_load_published_map_list_for_category(p_u_143, p144, p145, p_u_146) --[[ Name: load_published_map_list_for_category ]] --[[ Line: 468 ]]
    --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_6, (copy 3): v_u_9 ]]
    local v_u_147 = p_u_143._menus:push_menu(v_u_16:new(p_u_143, p_u_143._spui, p_u_143._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_143._evt:wait_on_event_once(v_u_6.EVT_Editor_GetPublishedMaps_Server, function(p148) --[[ Line: 470 ]]
        --[[ Upvalues: (copy 1): p_u_143, (copy 2): v_u_147, (copy 3): p_u_146, (ref 4): v_u_9 ]]
        p_u_143._menus:remove_menu(v_u_147)
        p_u_146(v_u_9.SavedMapInfo:info_list_from_table(p148))
    end)
    p_u_143._evt:fire_event_to_server(v_u_6.EVT_Editor_GetPublishedMaps_Client, p144, p145)
end;
v_u_42.show_published_map_list_ui = function(_, p_u_149, p150, p151, p_u_152) --[[ Name: show_published_map_list_ui ]] --[[ Line: 514 ]]
    --[[ Upvalues: (copy 1): v_u_42, (copy 2): f_load_published_map_list_for_category, (ref 3): v_u_18, (copy 4): v_u_8, (copy 5): v_u_1, (copy 6): f_load_custom_map_data_key, (ref 7): v_u_16, (copy 8): v_u_5, (ref 9): v_u_23, (copy 10): v_u_14, (copy 11): v_u_3, (copy 12): v_u_4, (copy 13): v_u_13, (copy 14): v_u_12 ]]
    v_u_42:move_camera_to_editor_position(p_u_149)
    f_load_published_map_list_for_category(p_u_149, p150, p151, function(p_u_153) --[[ Line: 516 ]]
        --[[ Upvalues: (ref 1): v_u_42, (copy 2): p_u_149, (ref 3): v_u_18, (ref 4): v_u_8, (ref 5): v_u_1, (ref 6): f_load_custom_map_data_key, (ref 7): v_u_16, (ref 8): v_u_5, (ref 9): v_u_23, (ref 10): v_u_14, (copy 11): p_u_152, (ref 12): v_u_3, (ref 13): v_u_4, (ref 14): v_u_13, (ref 15): v_u_12 ]]
        local v_u_154 = v_u_42:sort_published_map_info_list(p_u_149, p_u_153)
        local v_u_169 = p_u_149._menus:push_menu(v_u_18:new(p_u_149, p_u_149._spui, p_u_149._menus, function(p155) --[[ Line: 523 ]]
            --[[ Upvalues: (ref 1): v_u_154, (ref 2): v_u_8 ]]
            p155:set_header_text("Published Maps")
            for v156 = 1, v_u_154:count() do
                if v_u_8:singleton():contains_key(v_u_154:get(v156):get_source_songkey()) == true then
                    p155:get_element_list():push_front(v_u_154:get(v156))
                end;
            end;
        end, function(p157, p158, _, _, p159) --[[ Line: 530 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_1, (ref 3): v_u_8 ]]
            if #p157:get_custom_map_name() == 0 then
                p158.Text = "<EMPTY>"
            else
                p158.Text = p157:get_custom_map_name()
            end;
            v_u_42:list_element_render_saved_map_info(p159, p157)
            p159:set_select_button_enabled(true)
            p159:set_select_button_text("View")
            p159:get_description_display().Text = string.format("Creator: %s - Song: %s", p157:get_creator_name(), v_u_1:string_sub_max_len(v_u_8:singleton():get_title_for_key(p157:get_source_songkey()), 32))
        end, function(p160) --[[ Line: 546 ]]
            --[[ Upvalues: (ref 1): p_u_149, (ref 2): f_load_custom_map_data_key, (ref 3): v_u_16, (ref 4): v_u_5, (ref 5): v_u_23, (ref 6): v_u_14 ]]
            if p160 ~= nil then
                local v_u_161 = p_u_149
                local v_u_162 = p160:get_custom_map_data_key()
                f_load_custom_map_data_key(v_u_161, v_u_162, function(p163, p_u_164, p_u_165, p_u_166) --[[ Line: 82 ]]
                    --[[ Upvalues: (copy 1): v_u_161, (ref 2): v_u_16, (copy 3): v_u_162, (ref 4): v_u_5, (ref 5): v_u_23, (ref 6): v_u_14 ]]
                    if p163 ~= true then
                        return v_u_161._menus:push_menu(v_u_16:new(v_u_161, v_u_161._spui, v_u_161._menus):set_text("Error", string.format("Failed to load custom map data for key \'%s\'.", v_u_162)));
                    end;
                    local v_u_167 = v_u_161._lobby_join:get_lobby()
                    if v_u_167 == nil then
                        return v_u_5:warnf("SavedMapInfoListUI:show_load_map_code_ui() - lobby is nil");
                    end;
                    v_u_23:create_custom_map_preview_ui(v_u_161, p_u_165, p_u_164, p_u_166, function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_166, (copy 3): v_u_167, (copy 4): p_u_165, (copy 5): p_u_164 ]]
                        local v168 = v_u_14:new()
                        v168:set_rewarded_play(true)
                        v168:set_load_custom_map_additional_info(p_u_166)
                        v_u_167._spectate_manager:start_editor_custom_map_game(p_u_165, p_u_164, v168)
                    end)
                end)
            end;
        end, nil, nil, v_u_42:get_saved_map_info_list_select_ui_params())):set_do_not_update_while_camera_transitioning(true)
        v_u_42:list_select_ui_apply_settings(v_u_169)
        if p_u_152 ~= nil then
            p_u_152(v_u_169)
        end;
        v_u_18:set_filter_button_fns_list(v_u_169, (v_u_3:new({ function(p170) --[[ Line: 561 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_13, (ref 3): p_u_149, (ref 4): v_u_12 ]]
                v_u_4:set_button_text(p170, "\240\159\146\172 Chat")
                p170:bind_data(function() --[[ Line: 563 ]]
                    --[[ Upvalues: (ref 1): v_u_13, (ref 2): p_u_149, (ref 3): v_u_12 ]]
                    v_u_13:show_chat_menu(p_u_149, v_u_12.Category.PublishedMap, "", function(p171, _) --[[ Line: 564 ]]
                        p171:set_header_text("Published Map Chat")
                    end)
                end)
            end, function(p172) --[[ Line: 569 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_42, (ref 3): p_u_149, (ref 4): v_u_154, (copy 5): p_u_153, (copy 6): v_u_169 ]]
                v_u_4:set_button_text(p172, "\240\159\148\132 Sort")
                p172:bind_data(function() --[[ Line: 571 ]]
                    --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_149, (ref 3): v_u_154, (ref 4): p_u_153, (ref 5): v_u_169 ]]
                    v_u_42:update_sort_published_map_info_list_setings(p_u_149, function() --[[ Line: 572 ]]
                        --[[ Upvalues: (ref 1): v_u_154, (ref 2): v_u_42, (ref 3): p_u_149, (ref 4): p_u_153, (ref 5): v_u_169 ]]
                        v_u_154 = v_u_42:sort_published_map_info_list(p_u_149, p_u_153)
                        v_u_169:get_list_adapter():reset()
                        v_u_169:refresh()
                    end)
                end)
            end })))
    end)
end;
v_u_42.show_published_map_list_ui_for_songkey = function(_, p_u_173, p174) --[[ Name: show_published_map_list_ui_for_songkey ]] --[[ Line: 584 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_5, (copy 3): v_u_42, (copy 4): v_u_9, (copy 5): v_u_1, (copy 6): v_u_3, (copy 7): v_u_4, (ref 8): v_u_18 ]]
    local v_u_175 = v_u_8:singleton():get_audiomod_to_modes_of_songkey(p174):get(v_u_8.MOD_NORMAL)
    if v_u_8:singleton():contains_key(v_u_175) ~= true then
        return v_u_5:warnf("SavedMapInfoListUI:show_published_map_list_ui_for_songkey() - songkey \'%s\' does not exist in SongDatabase", (tostring(v_u_175)));
    end;
    v_u_42:show_published_map_list_ui(p_u_173, v_u_9.PublishCategory.SongKey, v_u_175, function(p_u_176) --[[ Line: 591 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (copy 3): v_u_175, (ref 4): v_u_3, (ref 5): v_u_4, (ref 6): v_u_42, (copy 7): p_u_173, (ref 8): v_u_18 ]]
        p_u_176:set_sub_text(string.format("Song: %s", v_u_1:string_sub_max_len(v_u_8:singleton():get_title_for_key(v_u_175), 32)))
        local v177 = v_u_3:new()
        v177:push_back(function(p178) --[[ Line: 601 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_42, (ref 3): p_u_173, (ref 4): v_u_175, (copy 5): p_u_176 ]]
            v_u_4:set_button_text(p178, "\226\158\149 Create Map")
            p178:bind_data(function() --[[ Line: 603 ]]
                --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_173, (ref 3): v_u_175 ]]
                v_u_42:create_new_map_for_song_key(p_u_173, v_u_175)
            end)
            v_u_4:button_add_enabled_anim(p178, function() --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): p_u_176 ]]
                return p_u_176:get_alpha();
            end)
            p178:set_enabled(v_u_42:test_can_local_player_create_new_map_for_song(p_u_173, v_u_175))
        end)
        v177:push_back(function(p179) --[[ Line: 613 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_42, (ref 3): p_u_173 ]]
            v_u_4:set_button_text(p179, "\240\159\147\157 Saved Maps")
            p179:bind_data(function() --[[ Line: 615 ]]
                --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_173 ]]
                v_u_42:show_player_recent_maps_ui(p_u_173)
            end)
        end)
        v_u_18:set_filter_button_fns_list(p_u_176, v177)
    end)
end;
local v_u_180 = nil
v_u_42.show_published_map_list_ui_for_artist_event = function(_, p_u_181) --[[ Name: show_published_map_list_ui_for_artist_event ]] --[[ Line: 625 ]]
    --[[ Upvalues: (ref 1): v_u_180, (ref 2): v_u_21, (copy 3): v_u_10, (copy 4): v_u_42, (copy 5): v_u_9, (copy 6): v_u_3, (copy 7): v_u_4, (copy 8): f_editor_song_select_test_songkey_filter, (copy 9): v_u_8, (ref 10): v_u_18 ]]
    if v_u_180 == nil then
        v_u_180 = v_u_21:create_info_state()
    end;
    local v182, v_u_183 = v_u_10:is_event_active(p_u_181._player_blob_manager:get_day_event_list())
    if v182 == true then
        v_u_42:show_published_map_list_ui(p_u_181, v_u_9.PublishCategory.ArtistEvent, v_u_183, function(p184) --[[ Line: 633 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_183, (ref 3): v_u_3, (ref 4): v_u_4, (ref 5): v_u_21, (copy 6): p_u_181, (ref 7): v_u_180, (ref 8): f_editor_song_select_test_songkey_filter, (ref 9): v_u_8, (ref 10): v_u_42, (ref 11): v_u_18 ]]
            p184:set_sub_text(string.format("Event: %s", v_u_10:get_event_info(v_u_183):get_title()))
            local v185 = v_u_3:new()
            v185:push_back(function(p186) --[[ Line: 643 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_21, (ref 3): p_u_181, (ref 4): v_u_180, (ref 5): f_editor_song_select_test_songkey_filter, (ref 6): v_u_8, (ref 7): v_u_42, (ref 8): v_u_10 ]]
                v_u_4:set_button_text(p186, "\226\158\149 Create Map")
                p186:bind_data(function() --[[ Line: 645 ]]
                    --[[ Upvalues: (ref 1): v_u_21, (ref 2): p_u_181, (ref 3): v_u_180, (ref 4): f_editor_song_select_test_songkey_filter, (ref 5): v_u_8, (ref 6): v_u_42, (ref 7): v_u_10 ]]
                    local v193 = v_u_21:new(p_u_181, v_u_180, function(p187) --[[ Line: 649 ]]
                        --[[ Upvalues: (ref 1): f_editor_song_select_test_songkey_filter ]]
                        return f_editor_song_select_test_songkey_filter(p187);
                    end, function(p188) --[[ Line: 652 ]]
                        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_42, (ref 3): p_u_181 ]]
                        if v_u_8:singleton():contains_key(p188) then
                            v_u_42:create_new_map_for_song_key(p_u_181, p188)
                        end;
                    end, function(p189) --[[ Line: 657 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_181, (ref 3): v_u_8 ]]
                        p189:clear()
                        local v190, v191 = v_u_10:is_event_active(p_u_181._player_blob_manager:get_day_event_list())
                        if v190 then
                            for v192, _ in v_u_10:get_playable_song_set(v191):key_itr() do
                                if v_u_8:singleton():key_get_audiomod(v192) == v_u_8.MOD_NORMAL then
                                    p189:add_set(v192)
                                end;
                            end;
                        end;
                    end)
                    v193.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 669 ]]
                        return "DebugEditorArtistEventSongSelectRestoreKey";
                    end;
                    p_u_181._menus:push_menu(v193)
                end)
            end)
            v185:push_back(function(p194) --[[ Line: 675 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_42, (ref 3): p_u_181 ]]
                v_u_4:set_button_text(p194, "\240\159\147\157 Saved Maps")
                p194:bind_data(function() --[[ Line: 677 ]]
                    --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_181 ]]
                    v_u_42:show_player_recent_maps_ui(p_u_181)
                end)
            end)
            v_u_18:set_filter_button_fns_list(p184, v185)
        end)
    end;
end;
v_u_42.move_camera_to_editor_position = function(_, p_u_195) --[[ Name: move_camera_to_editor_position ]] --[[ Line: 719 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_7, (copy 4): v_u_2, (ref 5): v_u_19, (copy 6): v_u_42 ]]
    v_u_1:ptry(function() --[[ Line: 720 ]]
        --[[ Upvalues: (copy 1): p_u_195, (ref 2): v_u_5, (ref 3): v_u_7, (ref 4): v_u_2, (ref 5): v_u_19, (ref 6): v_u_42 ]]
        local v196 = p_u_195._lobby_join:get_lobby()
        if v196 == nil then
            return v_u_5:warnf("SavedMapInfoListUI:move_camera_to_editor_position() - lobby is nil");
        end;
        v196:set_character_random_position_around_anchors_fn(function() --[[ Line: 723 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7:get_lobby_anchors().Editor.StandAnchor, v_u_7:get_lobby_anchors().Editor.LookAnchor;
        end)
        v196:transition_local_camera_to_anchors_fn(function() --[[ Line: 727 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7:get_lobby_anchors().Editor.CameraAnchor, v_u_7:get_lobby_anchors().Editor.LookAnchor;
        end)
        v196._ui_manager:remove_menus_with_anchors(v_u_2:new():add_set_from_table_list({ v_u_19:get_restore_menu_name(), v_u_42:get_editor_menu_restore_menu_name() }))
    end)
end;
local v_u_197 = true
local v_u_198 = 1
v_u_42.sort_published_map_info_list = function(_, _, p_u_199, _) --[[ Name: sort_published_map_info_list ]] --[[ Line: 747 ]]
    --[[ Upvalues: (copy 1): v_u_3, (ref 2): v_u_198, (ref 3): v_u_197, (copy 4): v_u_8 ]]
    return (function() --[[ Name: sort_and_create_list ]] --[[ Line: 748 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_199, (ref 3): v_u_198, (ref 4): v_u_197, (ref 5): v_u_8 ]]
        local v200 = v_u_3:new()
        for v201 = 1, p_u_199:count() do
            v200:push_back(p_u_199:get(v201))
        end;
        if v_u_198 == 1 then
            if v_u_197 ~= true then
                local v202 = v_u_3:new()
                for v203 = 1, v200:count() do
                    v202:push_front(v200:get(v203))
                end;
                return v202;
            end;
        else
            if v_u_198 == 2 then
                if v_u_197 == true then
                    v200:sort(function(p204, p205) --[[ Line: 764 ]]
                        return p204:get_assigned_difficulty() < p205:get_assigned_difficulty();
                    end)
                    return v200;
                else
                    v200:sort(function(p206, p207) --[[ Line: 768 ]]
                        return p206:get_assigned_difficulty() > p207:get_assigned_difficulty();
                    end)
                    return v200;
                end;
            end;
            if v_u_198 == 3 then
                local function _(p208) --[[ Name: get_saved_map_info_song_title ]] --[[ Line: 774 ]]
                    --[[ Upvalues: (ref 1): v_u_8 ]]
                    return string.lower(v_u_8:singleton():get_title_for_key(p208:get_source_songkey()));
                end;
                if v_u_197 == true then
                    v200:sort(function(p209, p210) --[[ Line: 778 ]]
                        --[[ Upvalues: (ref 1): v_u_8 ]]
                        return string.lower(v_u_8:singleton():get_title_for_key(p209:get_source_songkey())) < string.lower(v_u_8:singleton():get_title_for_key(p210:get_source_songkey()));
                    end)
                    return v200;
                else
                    v200:sort(function(p211, p212) --[[ Line: 782 ]]
                        --[[ Upvalues: (ref 1): v_u_8 ]]
                        return string.lower(v_u_8:singleton():get_title_for_key(p211:get_source_songkey())) > string.lower(v_u_8:singleton():get_title_for_key(p212:get_source_songkey()));
                    end)
                    return v200;
                end;
            end;
            if v_u_198 == 4 then
                local function _(p213) --[[ Name: get_saved_map_info_username ]] --[[ Line: 788 ]]
                    return string.lower(p213:get_creator_name());
                end;
                if v_u_197 == true then
                    v200:sort(function(p214, p215) --[[ Line: 792 ]]
                        return string.lower(p214:get_creator_name()) < string.lower(p215:get_creator_name());
                    end)
                    return v200;
                end;
                v200:sort(function(p216, p217) --[[ Line: 796 ]]
                    return string.lower(p216:get_creator_name()) > string.lower(p217:get_creator_name());
                end)
            end;
        end;
        return v200;
    end)();
end;
v_u_42.update_sort_published_map_info_list_setings = function(_, p218, p_u_219) --[[ Name: update_sort_published_map_info_list_setings ]] --[[ Line: 806 ]]
    --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_1, (ref 3): v_u_198, (ref 4): v_u_197, (copy 5): v_u_4, (copy 6): v_u_3 ]]
    local v226 = p218._menus:push_menu(v_u_18:new(p218, p218._spui, p218._menus, function(p220) --[[ Line: 812 ]]
        p220:set_header_text("Sort Published Maps")
        p220:get_element_list():push_back(1)
        p220:get_element_list():push_back(2)
        p220:get_element_list():push_back(3)
        p220:get_element_list():push_back(4)
    end, function(p221, p222, p223, _, p224) --[[ Line: 819 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_198 ]]
        if p221 == 1 then
            p222.Text = "Recent"
            p223.Image = v_u_1:important_assetid()
            p224:set_select_button_enabled(true)
            p224:get_description_display().Text = "Sort by most recent map."
        elseif p221 == 2 then
            p222.Text = "Difficulty"
            p223.Image = v_u_1:important_assetid()
            p224:set_select_button_enabled(true)
            p224:get_description_display().Text = "Sort by difficulty."
        elseif p221 == 3 then
            p222.Text = "Song"
            p223.Image = v_u_1:important_assetid()
            p224:set_select_button_enabled(true)
            p224:get_description_display().Text = "Sort by song title."
        elseif p221 == 4 then
            p222.Text = "Username"
            p223.Image = v_u_1:important_assetid()
            p224:set_select_button_enabled(true)
            p224:get_description_display().Text = "Sort by creator username."
        end;
        if p221 == v_u_198 then
            p222.Text = p222.Text .. " (Selected)"
        end;
    end, function(p225) --[[ Line: 850 ]]
        --[[ Upvalues: (ref 1): v_u_198, (copy 2): p_u_219 ]]
        if p225 ~= nil then
            v_u_198 = p225
        end;
        p_u_219()
    end)):set_close_on_element_select(true)
    local function _(p227) --[[ Name: update_button_text_sort_descending ]] --[[ Line: 859 ]]
        --[[ Upvalues: (ref 1): v_u_197, (ref 2): v_u_4 ]]
        if v_u_197 == true then
            v_u_4:set_button_text(p227, "\240\159\148\189 Descending")
        else
            v_u_4:set_button_text(p227, "\240\159\148\188 Ascending")
        end;
    end;
    local v228 = v_u_3:new()
    v228:push_back(function(p_u_229) --[[ Line: 869 ]]
        --[[ Upvalues: (ref 1): v_u_197, (ref 2): v_u_4 ]]
        if v_u_197 == true then
            v_u_4:set_button_text(p_u_229, "\240\159\148\189 Descending")
        else
            v_u_4:set_button_text(p_u_229, "\240\159\148\188 Ascending")
        end;
        p_u_229:bind_data(function() --[[ Line: 871 ]]
            --[[ Upvalues: (ref 1): v_u_197, (copy 2): p_u_229, (ref 3): v_u_4 ]]
            v_u_197 = not v_u_197
            local v230 = p_u_229
            if v_u_197 == true then
                v_u_4:set_button_text(v230, "\240\159\148\189 Descending")
            else
                v_u_4:set_button_text(v230, "\240\159\148\188 Ascending")
            end;
        end)
    end)
    v_u_18:set_filter_button_fns_list(v226, v228)
end;
return v_u_42;
