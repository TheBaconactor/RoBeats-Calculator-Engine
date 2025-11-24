-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:12 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.LocalShared.BGMManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local v_u_4 = require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
local v_u_5 = require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
local v_u_6 = require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
local v7 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
v7:require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_10, (ref 4): v_u_11, (ref 5): v_u_12 ]]
    v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_11 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI)
    v_u_12 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
end)
return {
    ["show_map_info_ui"] = function(_, p_u_13, p14, p15) --[[ Name: show_map_info_ui ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_3, (copy 4): v_u_2, (ref 5): v_u_10, (ref 6): v_u_12 ]]
        local v_u_16 = v_u_1:new({
            "Share Code",
            "Map Name",
            "Difficulty",
            "Song Title",
            "Song Artist",
            "Creator Name",
            "Creator RobloxID",
            "Last Edited Time",
            "Total Notes",
            "Approximate Song Length"
        })
        local v_u_17 = v_u_1:new({
            p14:get_custom_map_data_key(),
            p14:get_custom_map_name(),
            string.format("Difficulty: %s (Estimated: %d, Default: %d)", p14:get_assigned_difficulty_string(), v_u_6:editor_game_data_note_list_calculate_difficulty(p15:get_notes()), v_u_3:singleton():get_difficulty_for_key(p14:get_source_songkey())),
            v_u_3:singleton():get_title_for_key(p14:get_source_songkey()),
            v_u_3:singleton():get_artist_for_key(p14:get_source_songkey()),
            p14:get_creator_name(),
            p14:get_creator_rbxid(),
            os.date(nil, p14:get_last_edit_time()),
            p15:get_notes():count(),
            v_u_2:format_ms_time(math.floor((v_u_3:singleton():songkey_get_approx_length_sec(p14:get_source_songkey()))) * 1000)
        })
        p_u_13._menus:push_menu(v_u_10:new(p_u_13, p_u_13._spui, p_u_13._menus, function(p18) --[[ Line: 85 ]]
            p18:set_header_text("Map Info")
            for v19 = 1, 10 do
                p18:get_element_list():push_back(v19)
            end;
        end, function(p20, p21, p22, _, p23) --[[ Line: 91 ]]
            --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_2, (copy 3): v_u_17 ]]
            p21.Text = v_u_16:get(p20)
            p22.Image = v_u_2:get_question_assetid()
            p23:get_description_display().Text = tostring(v_u_17:get(p20))
        end, function(p_u_24) --[[ Line: 98 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_12, (copy 3): v_u_16, (copy 4): v_u_17 ]]
            if p_u_24 ~= nil then
                p_u_13._menus:push_menu(v_u_12:new(p_u_13):eval(function(p25) --[[ Line: 102 ]]
                    --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_24, (ref 3): v_u_17 ]]
                    p25:get_title_display().Text = "Map Info"
                    p25:get_sub_text_display().Text = v_u_16:get(p_u_24)
                    p25:get_text_box().Text = tostring(v_u_17:get(p_u_24))
                    p25:get_text_box().TextEditable = false
                    p25:get_text_box().TextSize = 26
                end))
            end;
        end)):set_close_on_element_select(false)
    end,
    ["show_map_share_code_menu"] = function(_, p26, p_u_27) --[[ Name: show_map_share_code_menu ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        p26._menus:push_menu(v_u_12:new(p26):eval(function(p28) --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): p_u_27 ]]
            p28:get_title_display().Text = "Share Map"
            p28:get_sub_text_display().Text = "Share this map with code:"
            p28:get_text_box().Text = p_u_27:get_custom_map_data_key()
            p28:get_text_box().TextEditable = false
            p28:get_text_box().TextSize = 32
            p28:select_all_text_box()
        end))
    end,
    ["show_map_chat_menu"] = function(_, p29, p_u_30) --[[ Name: show_map_chat_menu ]] --[[ Line: 132 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4 ]]
        v_u_5:show_chat_menu(p29, v_u_4.Category.CustomMap, p_u_30:get_custom_map_data_key(), function(p31, _) --[[ Line: 133 ]]
            --[[ Upvalues: (copy 1): p_u_30 ]]
            p31:set_header_text("Map Comments")
            p31:set_sub_text(string.format("Code: %s", p_u_30:get_custom_map_data_key()))
        end)
    end
};
