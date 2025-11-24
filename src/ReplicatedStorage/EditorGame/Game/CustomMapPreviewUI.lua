-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:15 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.LocalShared.BGMManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
local v_u_4 = require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
local v_u_5 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
local v6 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
v6:require_client(function() --[[ Line: 24 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_12 ]]
    v_u_7 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_10 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI)
    v_u_11 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
    v_u_12 = require(game.ReplicatedStorage.EditorGame.UI.CustomMapPreviewUI_Util)
end)
return {
    ["create_custom_map_preview_ui"] = function(_, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: create_custom_map_preview_ui ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_4, (ref 2): v_u_9, (copy 3): v_u_3, (copy 4): v_u_1, (copy 5): v_u_2, (copy 6): v_u_5, (ref 7): v_u_12 ]]
        local v_u_18 = v_u_4:editor_game_data_note_list_calculate_difficulty(p_u_15:get_notes())
        local v_u_19 = nil
        v_u_19 = p_u_13._menus:push_menu(v_u_9:new(p_u_13, p_u_13._spui, p_u_13._menus, function(p20) --[[ Line: 51 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_3 ]]
            p20:set_header_text("Custom Map")
            p20:set_sub_text(string.format("Code: %s", p_u_14:get_custom_map_data_key()))
            p20:get_element_list():push_back(1)
            p20:get_element_list():push_back(2)
            p20:get_element_list():push_back(3)
            p20:get_element_list():push_back(4)
            if v_u_3:validate_custom_map_key_components(p_u_14:get_custom_map_data_key()) then
                p20:get_element_list():push_back(6)
                p20:get_element_list():push_back(7)
            end;
            p20:get_element_list():push_back(8)
        end, function(p21, p22, p_u_23, _, p24) --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_14, (ref 3): v_u_2, (copy 4): v_u_18, (copy 5): p_u_16 ]]
            if p21 == 1 then
                p22.Text = "Play!"
                p_u_23.Image = v_u_1:get_double_arrow_icon_assetid()
                p24:get_description_display().Text = "Play this map!"
                p24:set_select_button_enabled(true)
                p24:set_select_button_text("Play!")
                return;
            elseif p21 == 2 then
                p22.Text = string.format("Map: %s", p_u_14:get_custom_map_name())
                v_u_1:get_user_thumbnail(p_u_14:get_creator_rbxid(), function(p25, _) --[[ Line: 75 ]]
                    --[[ Upvalues: (copy 1): p_u_23 ]]
                    if p_u_23 ~= nil then
                        p_u_23.Image = p25
                    end;
                end, false)
                p24:get_description_display().Text = string.format("Creator: %s", p_u_14:get_creator_name())
                p24:set_select_button_enabled(false)
                return;
            elseif p21 == 3 then
                p22.Text = string.format("Song: %s", v_u_1:string_sub_max_len(v_u_2:singleton():get_title_for_key(p_u_14:get_source_songkey()), 64))
                p_u_23.Image = v_u_2:singleton():get_coverimage_assetid_for_key(p_u_14:get_source_songkey())
                p24:get_description_display().Text = string.format("Artist: %s", v_u_2:singleton():get_artist_for_key(p_u_14:get_source_songkey()))
                p24:set_select_button_enabled(true)
                p24:set_select_button_text("View")
                return;
            elseif p21 == 4 then
                p22.Text = string.format("Difficulty: %s", p_u_14:get_assigned_difficulty_string())
                p_u_23.Image = v_u_1:important_assetid()
                p24:get_description_display().Text = string.format("Estimated: %d (Default: %d)", v_u_18, v_u_2:singleton():get_difficulty_for_key(p_u_14:get_source_songkey()))
                p24:set_select_button_enabled(false)
                return;
            elseif p21 == 6 then
                p22.Text = string.format("Likes: %d", p_u_14:get_like_count())
                p_u_23.Image = v_u_1:thumbs_up_assetid()
                if p_u_16:has_player_already_liked() then
                    p24:get_description_display().Text = "You have already liked this map."
                else
                    p24:get_description_display().Text = string.format("Play this map and give it a like \240\159\145\141!", p_u_14:get_like_count())
                end;
                p24:set_select_button_enabled(false)
                return;
            elseif p21 == 7 then
                p22.Text = "View Comments"
                p_u_23.Image = v_u_1:get_hud_button_chat_assetid()
                p24:get_description_display().Text = "View comments on this map."
                p24:set_select_button_enabled(true)
                p24:set_select_button_text("Open")
            elseif p21 == 8 then
                p22.Text = "Share Code"
                p_u_23.Image = v_u_1:plus_add_icon_assetid()
                p24:get_description_display().Text = "Share the code for this map."
                p24:set_select_button_enabled(true)
                p24:set_select_button_text("Share")
            end;
        end, function(p26) --[[ Line: 127 ]]
            --[[ Upvalues: (copy 1): p_u_17, (copy 2): p_u_13, (ref 3): v_u_19, (ref 4): v_u_5, (copy 5): p_u_14, (ref 6): v_u_12 ]]
            if p26 == nil then
                return;
            elseif p26 == 1 then
                p_u_17()
                p_u_13._menus:remove_menu(v_u_19)
                return;
            elseif p26 == 3 then
                v_u_5:show_song_info_popup(p_u_13, p_u_14:get_source_songkey())
                return;
            elseif p26 == 7 then
                v_u_12:show_map_chat_menu(p_u_13, p_u_14)
            elseif p26 == 8 then
                v_u_12:show_map_share_code_menu(p_u_13, p_u_14)
            end;
        end)):set_close_on_element_select(false):set_fn_info_button_pressed(function() --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_13, (copy 3): p_u_14, (copy 4): p_u_15 ]]
            v_u_12:show_map_info_ui(p_u_13, p_u_14, p_u_15)
        end)
        return v_u_19;
    end
};
