-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:51 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_2 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.GameStage.GameStageUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_6 = require(game.ReplicatedStorage.Shared.MatchMakingSettings)
local v_u_7 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_9 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_10 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_10 ]]
    v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
end)
local v_u_11 = {}
local v_u_12 = false
local v_u_13 = -1
v_u_11.artist_event_set_custom_stage_id = function(_, p14) --[[ Name: artist_event_set_custom_stage_id ]] --[[ Line: 29 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_10, (copy 3): v_u_6, (ref 4): v_u_13 ]]
    if not v_u_12 then
        v_u_6:set_selected_game_stage(v_u_10:get_local_matchmaking_settings(), p14)
        v_u_13 = p14
    end;
end;
v_u_11.set_artist_stage_manually_updated = function(_) --[[ Name: set_artist_stage_manually_updated ]] --[[ Line: 36 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = true
end;
v_u_11.set_custom_stage_id = function(_, p15) --[[ Name: set_custom_stage_id ]] --[[ Line: 40 ]]
    --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_6, (ref 3): v_u_13 ]]
    v_u_6:set_selected_game_stage(v_u_10:get_local_matchmaking_settings(), p15)
    v_u_13 = p15
end;
v_u_11.new = function(_, p_u_16, p_u_17, _, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_1, (copy 3): v_u_6, (ref 4): v_u_10, (copy 5): v_u_5, (copy 6): v_u_7, (copy 7): v_u_8, (ref 8): v_u_13, (copy 9): v_u_9, (copy 10): v_u_2, (copy 11): v_u_3, (copy 12): v_u_11 ]]
    local v20 = {}
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 55 ]]
        --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_22, (ref 3): v_u_4, (ref 4): v_u_21, (ref 5): v_u_1, (copy 6): p_u_19, (copy 7): p_u_18, (ref 8): v_u_24, (ref 9): v_u_25, (ref 10): v_u_6, (ref 11): v_u_10, (ref 12): v_u_23, (ref 13): v_u_5, (ref 14): v_u_7, (ref 15): v_u_8, (ref 16): v_u_13, (ref 17): v_u_9, (ref 18): v_u_2, (copy 19): p_u_17, (ref 20): v_u_3, (ref 21): v_u_11 ]]
        v_u_22 = v_u_4:playerblob_get_available_stage_ids_list_for_day_event_list_and_event_info(p_u_16._player_blob_manager:get_player_blob(), p_u_16._player_blob_manager:get_day_event_list(), p_u_16._game_join_protocol:get_event_info(), p_u_16._player_blob_manager:get_cached_collection_info())
        v_u_21 = v_u_1:new(p_u_19, p_u_18.MainSurface, p_u_18.StageSelectPanel.MainSurface)
        local l_Frame_0 = p_u_18.StageSelectPanel.MainSurface.SurfaceGui.Frame
        v_u_24 = l_Frame_0.IconNew
        v_u_25 = l_Frame_0.IconEvent
        v_u_24.Visible = false
        v_u_25.Visible = false
        local l_PageDisplay_0 = l_Frame_0.PageDisplay
        local l_StageNameDisplay_0 = l_Frame_0.StageNameDisplay
        local l_Icon_0 = l_Frame_0.Icon
        local v26 = v_u_6:get_selected_game_stage(v_u_10:get_local_matchmaking_settings())
        local v27 = 0
        for v28 = 1, v_u_22:count() do
            if v_u_22:get(v28) == v26 then
                v27 = v28 - 1
                break;
            end;
        end;
        v_u_23 = v_u_5:new():set_fn_get_data_list(function() --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end):set_fn_set_element_data(function(_, p29) --[[ Line: 96 ]]
            --[[ Upvalues: (copy 1): l_StageNameDisplay_0, (ref 2): v_u_4, (copy 3): l_Icon_0, (ref 4): v_u_24, (ref 5): v_u_7, (ref 6): v_u_25, (ref 7): p_u_16, (ref 8): v_u_8, (ref 9): v_u_13, (ref 10): v_u_10, (ref 11): v_u_6, (ref 12): p_u_19, (ref 13): v_u_9 ]]
            l_StageNameDisplay_0.Text = v_u_4:get_name_for_stage_id(p29)
            l_Icon_0.Image = v_u_4:get_icon_for_stage_id(p29)
            v_u_24.Visible = v_u_7:singleton():is_stage_new(p29)
            local v30 = v_u_25
            local v31
            if p_u_16._game_join_protocol:get_event_info() == v_u_8.EventMission.ArtistEvent then
                v31 = p29 == v_u_13
            else
                v31 = false
            end;
            v30.Visible = v31
            local v32 = v_u_10:get_local_matchmaking_settings()
            if v_u_6:get_selected_game_stage(v32) ~= p29 then
                v_u_6:set_selected_game_stage(v32, p29)
                p_u_19:push_matchmaking_settings()
                p_u_16._player_settings_manager:set_key_no_changes(v_u_9.Key.SelectedGameStage, p29)
            end;
        end):set_do_wrap(true):set_fn_update_page_display(function(p33, p34) --[[ Line: 111 ]]
            --[[ Upvalues: (copy 1): l_PageDisplay_0 ]]
            l_PageDisplay_0.Text = string.format("%d / %d", p33, p34)
        end):set_do_wrap(true):set_i_offset(v27)
        v_u_23:push_display_element({})
        v_u_23:page_update()
        p_u_19:add_cycle_element(p_u_16, 1, v_u_2:new(v_u_1:new(v_u_21, v_u_21:get_child_part(), p_u_18.StageSelectPanel.ArrowLeft), p_u_17, function() --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_3, (ref 3): v_u_11, (ref 4): v_u_23 ]]
            p_u_16._sfx_manager:play_sfx(v_u_3.SFX_BUTTONPRESS)
            v_u_11:set_artist_stage_manually_updated()
            v_u_23:prev_page()
        end))
        p_u_19:add_cycle_element(p_u_16, 1, v_u_2:new(v_u_1:new(v_u_21, v_u_21:get_child_part(), p_u_18.StageSelectPanel.ArrowRight), p_u_17, function() --[[ Line: 132 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_3, (ref 3): v_u_11, (ref 4): v_u_23 ]]
            p_u_16._sfx_manager:play_sfx(v_u_3.SFX_BUTTONPRESS)
            v_u_11:set_artist_stage_manually_updated()
            v_u_23:next_page()
        end))
    end;
    v20.layout = function(_) --[[ Name: layout ]] --[[ Line: 140 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21:layout()
    end;
    f_cons()
    return v20;
end;
return v_u_11;
