-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
local v_u_7 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v10 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
v10:require_client(function() --[[ Line: 38 ]]
    --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_16, (ref 7): v_u_17, (ref 8): v_u_18, (ref 9): v_u_19 ]]
    v_u_11 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_14 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI)
    v_u_15 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.SongSelectV3UI)
    v_u_17 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI_Util)
    v_u_18 = require(game.ReplicatedStorage.EditorGame.UI.CustomMapPreviewUI_Util)
    v_u_19 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
end)
local v_u_20 = {}
v_u_20.try_publish_saved_map_info = function(_, p_u_21, p_u_22, p_u_23) --[[ Name: try_publish_saved_map_info ]] --[[ Line: 52 ]]
    --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_4, (copy 3): v_u_7, (copy 4): v_u_1, (ref 5): v_u_13, (copy 6): v_u_8, (ref 7): v_u_18, (ref 8): v_u_19, (copy 9): v_u_3, (copy 10): v_u_20 ]]
    local function f_do_publish_saved_map_info() --[[ Name: do_publish_saved_map_info ]] --[[ Line: 53 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_11, (ref 3): v_u_4, (ref 4): v_u_7, (copy 5): p_u_22, (ref 6): v_u_1 ]]
        local v_u_24 = p_u_21._menus:push_menu(v_u_11:new(p_u_21, p_u_21._spui, p_u_21._menus):set_text("Publishing...", "Please wait..."):set_close_button_visible(false))
        p_u_21._evt:wait_on_event_once(v_u_4.EVT_Editor_PublishCustomMap_Server, function(p25, p26, p_u_27, _) --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): p_u_21, (copy 2): v_u_24, (ref 3): v_u_11, (ref 4): v_u_7, (ref 5): p_u_22, (ref 6): v_u_1 ]]
            if p25 ~= true then
                p_u_21._menus:remove_menu(v_u_24)
                return p_u_21._menus:push_menu(v_u_11:new(p_u_21, p_u_21._spui, p_u_21._menus):set_text("Error", p26));
            end;
            p_u_21._player_blob_manager:do_sync(function() --[[ Line: 64 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_24, (ref 3): v_u_7, (copy 4): p_u_27, (ref 5): p_u_22, (ref 6): v_u_1, (ref 7): v_u_11 ]]
                p_u_21._menus:remove_menu(v_u_24)
                local v28 = v_u_7.CheckPublishInfo:from_table(p_u_27)
                local v29 = string.format("Map: %s [%s]\nHas been published in categories:\n", p_u_22:get_custom_map_name(), p_u_22:get_custom_map_data_key())
                for _, v30 in v_u_7.PublishCategory:all_publish_categories_list():key_itr() do
                    if v28:get_publish_category_is_published(v30) == true then
                        v29 = v29 .. string.format(" - %s\n", v_u_1:enum_val_to_name(v30, v_u_7.PublishCategory))
                    end;
                end;
                p_u_21._menus:push_menu(v_u_11:new(p_u_21, p_u_21._spui, p_u_21._menus):set_text("Published", v29))
            end)
        end)
        p_u_21._evt:fire_event_to_server(v_u_4.EVT_Editor_PublishCustomMap_Client, p_u_22:to_table())
    end;
    local function f_show_publish_info_popup(p31) --[[ Name: show_publish_info_popup ]] --[[ Line: 88 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_21, (ref 3): v_u_1, (ref 4): v_u_13, (copy 5): p_u_22, (ref 6): v_u_8, (copy 7): f_do_publish_saved_map_info, (ref 8): v_u_18, (copy 9): p_u_23 ]]
        local v_u_32 = v_u_7.CheckPublishInfo:from_table(p31)
        local v_u_33 = p_u_21._player_blob_manager:get_player_blob()
        local v_u_34 = false
        local v_u_35 = ""
        for _, v36 in v_u_7.PublishCategory:all_publish_categories_list():key_itr() do
            v_u_34 = v_u_34 or v_u_32:get_publish_category_is_published(v36)
            if v_u_32:get_publish_category_is_published(v36) == true then
                local v37 = v_u_1:enum_val_to_name(v36, v_u_7.PublishCategory)
                if #v_u_35 == 0 then
                    v_u_35 = string.format("%s", v37)
                else
                    v_u_35 = v_u_35 .. string.format(", %s", v37)
                end;
            end;
        end;
        local v_u_38 = nil
        v_u_38 = p_u_21._menus:push_menu(v_u_13:new(p_u_21, p_u_21._spui, p_u_21._menus, function(p39) --[[ Line: 113 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): p_u_22, (ref 3): v_u_35 ]]
            p39:set_header_text(v_u_34 and "Re-Publish Map?" or "Publish Map?")
            p39:set_sub_text(string.format("Map: %s\n%s", p_u_22:get_custom_map_data_key(), v_u_34 and string.format("This map has already been published in categories:\n%s", v_u_35) or "This map has not been published yet."))
            p39:get_element_list():push_back("Publish Map")
            p39:get_element_list():push_back("Cost")
        end, function(p40, p41, p42, _, p43) --[[ Line: 127 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_32, (ref 3): v_u_8, (copy 4): v_u_33 ]]
            if p40 == "Publish Map" then
                p41.Text = "Publish"
                p42.Image = v_u_1:get_iconhd_mission()
                p43:set_select_button_enabled(true)
                p43:set_select_button_text("Publish")
                p43:get_description_display().Text = "Publish this map!"
            elseif p40 == "Cost" then
                p41.Text = string.format("Cost: %d Stars", v_u_32:get_publish_cost_star_currency())
                p42.Image = v_u_8:currency_type_get_image(v_u_8.CurrencyType.Stars)
                p43:get_description_display().Text = string.format("You Have: %d Stars", v_u_8:get_star_currency(v_u_33))
                p43:set_select_button_enabled(false)
                p43:set_select_button_text("View")
            end;
        end, function(p44) --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_38, (ref 3): f_do_publish_saved_map_info ]]
            if p44 ~= nil then
                if p44 == "Publish Map" then
                    p_u_21._menus:remove_menu(v_u_38)
                    f_do_publish_saved_map_info()
                end;
            end;
        end, nil, v_u_13:get_popup_text_list_ui_obj())):set_close_on_element_select(false):set_refresh_on_refocus(true):set_fn_info_button_pressed(function() --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): p_u_21, (ref 3): p_u_22, (ref 4): p_u_23 ]]
            v_u_18:show_map_info_ui(p_u_21, p_u_22, p_u_23)
        end)
    end;
    local function f_do_check_publish_info() --[[ Name: do_check_publish_info ]] --[[ Line: 159 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_11, (ref 3): v_u_4, (copy 4): f_show_publish_info_popup, (copy 5): p_u_22 ]]
        local v_u_45 = p_u_21._menus:push_menu(v_u_11:new(p_u_21, p_u_21._spui, p_u_21._menus):set_text("Loading", "Please wait..."):set_close_button_visible(false))
        p_u_21._evt:wait_on_event_once(v_u_4.EVT_Editor_CheckPublishInfo_Server, function(p46, p47, p48) --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): p_u_21, (copy 2): v_u_45, (ref 3): v_u_11, (ref 4): f_show_publish_info_popup ]]
            p_u_21._menus:remove_menu(v_u_45)
            if p46 ~= true then
                return p_u_21._menus:push_menu(v_u_11:new(p_u_21, p_u_21._spui, p_u_21._menus):set_text("Error", p47));
            end;
            f_show_publish_info_popup(p48)
        end)
        p_u_21._evt:fire_event_to_server(v_u_4.EVT_Editor_CheckPublishInfo_Client, p_u_22:to_table())
    end;
    local function f_do_check_custom_map_name() --[[ Name: do_check_custom_map_name ]] --[[ Line: 174 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_19, (copy 3): p_u_21, (copy 4): f_do_check_publish_info ]]
        local v49 = p_u_22:get_custom_map_name()
        local v50 = p_u_22:get_default_custom_map_name()
        if #v49 == 0 or v49 == v50 then
            v_u_19:message_box_confirm(p_u_21, function() --[[ Line: 180 ]]
                --[[ Upvalues: (ref 1): f_do_check_publish_info ]]
                f_do_check_publish_info()
            end, "Map Name is Empty", string.format("Are you sure you want to publish this map without a name?\nIt will use the default name \"%s\" if published.", v50))
        else
            f_do_check_publish_info()
        end;
    end;
    if p_u_23:get_notes():count() <= 15 then
        v_u_3:puts("Map note count: %d", p_u_23:get_notes():count())
        return p_u_21._menus:push_menu(v_u_11:new(p_u_21, p_u_21._spui, p_u_21._menus):set_text("Error", "Map must have at least a minimum number of notes to be published."));
    end;
    v_u_20:check_saved_map_info_and_custom_map_data_is_different_from_default(p_u_21, p_u_22, p_u_23, function(p51) --[[ Line: 196 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_11, (copy 3): f_do_check_custom_map_name ]]
        if p51 ~= true then
            return p_u_21._menus:push_menu(v_u_11:new(p_u_21, p_u_21._spui, p_u_21._menus):set_text("Error", "Map must have enough changes from default in order to be published."));
        end;
        f_do_check_custom_map_name()
    end)
end;
local function f_note_data_list_is_different_enough(p52, p53) --[[ Name: note_data_list_is_different_enough ]] --[[ Line: 205 ]]
    --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_17, (copy 3): v_u_9 ]]
    local v54 = v_u_2:new()
    for _, v55 in p52:key_itr() do
        v54:add_set(v_u_17:note_data_to_osu_string(v55))
    end;
    local v56 = v_u_2:new()
    for _, v57 in p53:key_itr() do
        v56:add_set(v_u_17:note_data_to_osu_string(v57))
    end;
    local v58 = v_u_2:set_union(v54, v56)
    local v59 = 0
    for v60, _ in v54:key_itr() do
        if not v56:contains(v60) then
            v59 = v59 + 1
        end;
    end;
    local v61 = 0
    for v62, _ in v56:key_itr() do
        if not v54:contains(v62) then
            v61 = v61 + 1
        end;
    end;
    local v63 = string.format("note_data_list_is_similar count_a_only(%d) count_b_only(%d) union_count(%d)", v59, v61, v58:count())
    if v_u_9.DoPublishMapCheckDifferences == true then
        return v59 + v61 > 15, v63;
    else
        return true, v63;
    end;
end;
v_u_20.check_saved_map_info_and_custom_map_data_is_different_from_default = function(_, p_u_64, p65, p_u_66, p_u_67) --[[ Name: check_saved_map_info_and_custom_map_data_is_different_from_default ]] --[[ Line: 238 ]]
    --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_5, (copy 3): v_u_7, (copy 4): v_u_6, (copy 5): f_note_data_list_is_different_enough, (copy 6): v_u_3 ]]
    local v_u_68 = v_u_11:loading_menu(p_u_64)
    v_u_5:singleton():get_data_for_key(p65:get_source_songkey(), function(p69) --[[ Line: 240 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_6, (ref 3): f_note_data_list_is_different_enough, (copy 4): p_u_66, (ref 5): v_u_3, (ref 6): v_u_11, (copy 7): p_u_64, (copy 8): v_u_68, (copy 9): p_u_67 ]]
        local v70 = v_u_7.CustomMapData:new()
        for v71 = 1, #p69.HitObjects do
            v70:get_notes():push_back((v_u_6.Note:from_table(p69.HitObjects[v71])))
        end;
        local v72, v73 = f_note_data_list_is_different_enough(v70:get_notes(), p_u_66:get_notes())
        v_u_3:puts(v73)
        v_u_11:remove_loading_menu(p_u_64, v_u_68)
        p_u_67(v72)
    end)
end;
v_u_20.show_map_saved_popup = function(_, p_u_74, _, p_u_75, p_u_76) --[[ Name: show_map_saved_popup ]] --[[ Line: 255 ]]
    --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_1, (copy 3): v_u_20, (ref 4): v_u_18 ]]
    local v_u_77 = nil
    v_u_77 = p_u_74._menus:push_menu(v_u_13:new(p_u_74, p_u_74._spui, p_u_74._menus, function(p78) --[[ Line: 264 ]]
        --[[ Upvalues: (copy 1): p_u_75 ]]
        p78:set_header_text("Map Saved")
        p78:set_sub_text(string.format("Saved to code \'%s\'.\nAssigned Difficulty: %s.", p_u_75:get_custom_map_data_key(), p_u_75:get_assigned_difficulty_string()))
        p78:get_element_list():push_back("Publish Map")
        p78:get_element_list():push_back("Share Map Code")
    end, function(p79, p80, p81, _, p82) --[[ Line: 276 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        if p79 == "Publish Map" then
            p80.Text = "Publish Map"
            p81.Image = v_u_1:get_iconhd_mission()
            p82:set_select_button_enabled(true)
            p82:set_select_button_text("Publish")
            p82:get_description_display().Text = "Learn more about publishing this map."
        elseif p79 == "Share Map Code" then
            p80.Text = "Share Code"
            p81.Image = v_u_1:plus_add_icon_assetid()
            p82:get_description_display().Text = "Share the code for this map."
            p82:set_select_button_enabled(true)
            p82:set_select_button_text("Share")
        end;
    end, function(p83) --[[ Line: 292 ]]
        --[[ Upvalues: (copy 1): p_u_74, (ref 2): v_u_77, (ref 3): v_u_20, (copy 4): p_u_75, (copy 5): p_u_76, (ref 6): v_u_18 ]]
        if p83 == nil then
            return;
        elseif p83 == "Publish Map" then
            p_u_74._menus:remove_menu(v_u_77)
            v_u_20:try_publish_saved_map_info(p_u_74, p_u_75, p_u_76)
        elseif p83 == "Share Map Code" then
            v_u_18:show_map_share_code_menu(p_u_74, p_u_75)
        end;
    end, nil, v_u_13:get_popup_text_list_ui_obj())):set_close_on_element_select(false):set_refresh_on_refocus(true):set_fn_info_button_pressed(function() --[[ Line: 306 ]]
        --[[ Upvalues: (ref 1): v_u_18, (copy 2): p_u_74, (copy 3): p_u_75, (copy 4): p_u_76 ]]
        v_u_18:show_map_info_ui(p_u_74, p_u_75, p_u_76)
    end)
end;
return v_u_20;
