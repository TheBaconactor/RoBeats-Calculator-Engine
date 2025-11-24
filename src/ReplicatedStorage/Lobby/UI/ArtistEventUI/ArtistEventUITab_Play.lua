-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:58 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_8 = require(game.ReplicatedStorage.Lobby.UI.TabControllerBase)
local v_u_9 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_10 = require(game.ReplicatedStorage.AudioData.NewSongInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.AudioRank)
local v12 = {}
local v_u_27 = {
    ["new"] = function(_, p_u_13, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_7, (copy 6): v_u_10, (copy 7): v_u_1, (copy 8): v_u_11 ]]
        local v17 = {}
        local v_u_18 = nil
        local v_u_19 = nil
        local l_Frame_0 = p_u_16.PrimaryPart.SurfaceGui.Frame
        local l_Background_0 = l_Frame_0.Background
        local l_NewDisplay_0 = l_Frame_0.NewDisplay
        local v_u_20 = l_Frame_0:FindFirstChild("RankDisplay")
        if v_u_20 then
            v_u_20.Visible = false
        end;
        local l_FavoriteDisplay_0 = l_Frame_0.FavoriteDisplay
        v17.cons = function(_) --[[ Name: cons ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_18, (copy 2): p_u_15, (copy 3): p_u_13, (ref 4): v_u_3, (ref 5): v_u_2, (copy 6): p_u_16, (ref 7): v_u_4, (ref 8): v_u_19, (copy 9): p_u_14 ]]
            v_u_18 = p_u_15:add_cycle_element(p_u_13, 1, v_u_3:new(v_u_2:new(p_u_15, p_u_15:get_uichild_parent(), p_u_16.PrimaryPart), p_u_13._spui, function() --[[ Line: 45 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (ref 3): v_u_19, (ref 4): p_u_14 ]]
                p_u_13._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                if v_u_19 then
                    p_u_14:on_songkey_pressed(v_u_19)
                end;
            end)):set_auto_zoffset_behaviour(true)
        end;
        local v_u_21 = -1
        v17.set_display_element = function(_, p22) --[[ Name: set_display_element ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_19, (copy 2): v_u_20, (ref 3): v_u_21, (ref 4): v_u_18, (copy 5): l_Frame_0, (ref 6): v_u_5, (ref 7): v_u_7, (copy 8): l_NewDisplay_0, (ref 9): v_u_10, (copy 10): l_FavoriteDisplay_0, (copy 11): p_u_13 ]]
            v_u_19 = p22
            if v_u_20 then
                v_u_20.Visible = false
                v_u_21 = -1
            end;
            if v_u_19 then
                v_u_18:set_visible(true)
                l_Frame_0.SongDifficultySection.Display.TextColor3 = v_u_5:singleton():get_difficulty_color_for_key(v_u_19)
                l_Frame_0.SongDifficultySection.Display.Text = tostring(v_u_5:singleton():get_difficulty_for_key(v_u_19))
                v_u_5:singleton():render_coverimage_for_key(l_Frame_0.Icon, l_Frame_0.IconOverlay, v_u_19)
                v_u_7:render_songkey_colorsection(v_u_19, l_Frame_0.ColorSection)
                l_NewDisplay_0.Visible = v_u_10:songkey_is_new(v_u_19)
                l_FavoriteDisplay_0.Visible = p_u_13._player_blob_manager:is_songkey_favorite(v_u_19)
            else
                v_u_18:set_visible(false)
            end;
        end;
        v17.get_data = function(_) --[[ Name: get_data ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v17.set_selected = function(_, p23) --[[ Name: set_selected ]] --[[ Line: 76 ]]
            --[[ Upvalues: (copy 1): l_Background_0, (ref 2): v_u_1 ]]
            if p23 then
                l_Background_0.Image = v_u_1:get_song_container_selected_assetid()
            else
                l_Background_0.Image = v_u_1:get_song_container_assetid()
            end;
        end;
        v17.set_visible = function(_, p24) --[[ Name: set_visible ]] --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18:set_visible(p24)
        end;
        v17.layout = function(_) end;
        v17.behaviour_update = function(_, _) --[[ Name: behaviour_update ]] --[[ Line: 90 ]]
            --[[ Upvalues: (copy 1): v_u_20, (ref 2): v_u_5, (ref 3): v_u_19, (ref 4): v_u_21, (copy 5): p_u_13, (ref 6): v_u_11 ]]
            if v_u_20 and (v_u_5:singleton():contains_key(v_u_19) and v_u_21 ~= p_u_13._player_song_stats_manager:get_time_last_update()) then
                v_u_21 = p_u_13._player_song_stats_manager:get_time_last_update()
                local v25, v26 = p_u_13._player_song_stats_manager:get_best_grade_rank_value(v_u_19)
                if v26 > 0 then
                    v_u_20.Image = v_u_11:get_rank_value_icon(v25)
                    v_u_20.Visible = true
                    return;
                end;
                v_u_20.Visible = false
            end;
        end;
        v17:cons()
        return v17;
    end
}
local v_u_28 = 0
v12.new = function(_, p_u_29, p_u_30, p_u_31) --[[ Name: new ]] --[[ Line: 109 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_4, (copy 5): v_u_6, (copy 6): v_u_5, (copy 7): v_u_9, (ref 8): v_u_28, (copy 9): v_u_27 ]]
    local v32 = v_u_8:new()
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = nil
    local v_u_38 = nil
    local v_u_39 = nil
    v32.cons = function(p_u_40) --[[ Name: cons ]] --[[ Line: 118 ]]
        --[[ Upvalues: (ref 1): v_u_33, (copy 2): p_u_31, (ref 3): v_u_37, (ref 4): v_u_38, (ref 5): v_u_39, (copy 6): p_u_30, (copy 7): p_u_29, (ref 8): v_u_3, (ref 9): v_u_2, (ref 10): v_u_4, (ref 11): v_u_35, (ref 12): v_u_34, (ref 13): v_u_36, (ref 14): v_u_6, (ref 15): v_u_5, (ref 16): v_u_9, (ref 17): v_u_28, (ref 18): v_u_27 ]]
        v_u_33 = p_u_31.MainSurface.SurfaceGui.Frame.TabPlay
        v_u_33.Visible = false
        v_u_37 = v_u_33.PageDisplaySection.CurrentPageDisplay
        v_u_38 = v_u_33.PageDisplaySection.MaxPageDisplay
        v_u_39 = p_u_30:add_cycle_element(p_u_29, 1, v_u_3:new(v_u_2:new(p_u_30, p_u_31.PrimaryPart, p_u_31.TabPlayElements.PlayButton), p_u_29._spui, function() --[[ Line: 128 ]]
            --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (ref 3): p_u_30 ]]
            p_u_29._sfx_manager:play_sfx(v_u_4.SFX_MENU_OPEN)
            p_u_30:play_button_pressed()
        end))
        v_u_39:set_visible(false)
        v_u_35 = p_u_30:add_cycle_element(p_u_29, 1, v_u_3:new(v_u_2:new(p_u_30, p_u_31.PrimaryPart, p_u_31.TabPlayElements.ArrowLeft), p_u_29._spui, function() --[[ Line: 138 ]]
            --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (ref 3): v_u_34 ]]
            p_u_29._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
            v_u_34:prev_page()
        end))
        v_u_36 = p_u_30:add_cycle_element(p_u_29, 1, v_u_3:new(v_u_2:new(p_u_30, p_u_31.PrimaryPart, p_u_31.TabPlayElements.ArrowRight), p_u_29._spui, function() --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (ref 3): v_u_34 ]]
            p_u_29._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
            v_u_34:next_page()
        end))
        local v_u_41 = v_u_6:get_event_info(p_u_30:get_event_id()):get_songs_list()
        v_u_41:remove_if(function(p42) --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            return v_u_5:singleton():get_songkey_priority(p42) == v_u_5.SongPriority.Hidden;
        end)
        v_u_41:sort(function(p43, p44) --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            local v45 = v_u_5:singleton():get_difficulty_for_key(p43)
            local v46 = v_u_5:singleton():get_difficulty_for_key(p44)
            if v45 == v46 then
                return p43 - p44;
            else
                return v46 - v45;
            end;
        end)
        v_u_34 = v_u_9:new():set_fn_get_data_list(function() --[[ Line: 167 ]]
            --[[ Upvalues: (copy 1): v_u_41 ]]
            return v_u_41;
        end):set_fn_set_element_data(function(p47, p48) --[[ Line: 168 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_30 ]]
            if p48 == nil or not v_u_5:singleton():contains_key(p48) then
                p47:set_visible(false)
                p47:set_selected(false)
            else
                p47:set_visible(true)
                p47:set_display_element(p48)
                p47:set_selected(p48 == p_u_30:get_selected_songkey())
            end;
        end):set_fn_next_prev_visible(function(p49, p50) --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_35 ]]
            v_u_36:set_visible(p49)
            v_u_35:set_visible(p50)
        end):set_fn_update_page_display(function(p51, p52) --[[ Line: 182 ]]
            --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_38 ]]
            v_u_37.Text = tostring(p51)
            v_u_38.Text = tostring(p52)
        end):set_do_wrap(true):set_i_offset(v_u_28):set_fn_store_i_offset(function(p53) --[[ Line: 188 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28 = p53
        end)
        local l_Anchors_0 = p_u_31.TabPlayElements.Anchors
        v_u_34:create_list_elements_from_anchors_and_proto({
            l_Anchors_0.Anchor1,
            l_Anchors_0.Anchor2,
            l_Anchors_0.Anchor3,
            l_Anchors_0.Anchor4,
            l_Anchors_0.Anchor5,
            l_Anchors_0.Anchor6,
            l_Anchors_0.Anchor7,
            l_Anchors_0.Anchor8
        }, p_u_31.TabPlayElements.Proto, p_u_31, function(p54) --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): p_u_29, (copy 3): p_u_40, (ref 4): p_u_30 ]]
            return v_u_27:new(p_u_29, p_u_40, p_u_30, p54);
        end)
        p_u_40:refresh()
    end;
    v32.on_songkey_pressed = function(_, p55) --[[ Name: on_songkey_pressed ]] --[[ Line: 213 ]]
        --[[ Upvalues: (copy 1): p_u_30, (ref 2): v_u_34, (ref 3): v_u_5, (ref 4): v_u_39 ]]
        p_u_30:preview_songkey(p55)
        for _, v56 in v_u_34:get_display_elements():key_itr() do
            v56:set_selected(v56:get_data() == p55)
        end;
        if p_u_30:get_selected_songkey() ~= v_u_5:invalid_songkey() then
            v_u_39:set_visible(true)
        end;
    end;
    v32.set_visible = function(_, p57) --[[ Name: set_visible ]] --[[ Line: 223 ]]
        --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_34, (copy 3): p_u_30, (ref 4): v_u_5, (ref 5): v_u_39 ]]
        v_u_33.Visible = p57
        v_u_34:set_visible(p57)
        if p57 and p_u_30:get_selected_songkey() ~= v_u_5:invalid_songkey() then
            v_u_39:set_visible(true)
        else
            v_u_39:set_visible(false)
        end;
    end;
    v32.load_data = function(_, p58) --[[ Name: load_data ]] --[[ Line: 232 ]]
        p58()
    end;
    v32.refresh = function(_) --[[ Name: refresh ]] --[[ Line: 233 ]]
        --[[ Upvalues: (ref 1): v_u_34, (copy 2): p_u_30, (ref 3): v_u_5, (ref 4): v_u_39 ]]
        v_u_34:page_update()
        if p_u_30:get_selected_songkey() ~= v_u_5:invalid_songkey() then
            v_u_39:set_visible(true)
        end;
    end;
    v32.layout = function(_) --[[ Name: layout ]] --[[ Line: 239 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        v_u_34:layout()
    end;
    v32.requires_reload_on_menu_refocus = function(_) --[[ Name: requires_reload_on_menu_refocus ]] --[[ Line: 242 ]]
        return false;
    end;
    v32.behaviour_update = function(_, p59) --[[ Name: behaviour_update ]] --[[ Line: 243 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        for _, v60 in v_u_34:get_display_elements():key_itr() do
            v60:behaviour_update(p59)
        end;
    end;
    v32.is_settings_section_visible = function(_) --[[ Name: is_settings_section_visible ]] --[[ Line: 250 ]]
        return true;
    end;
    v32:cons()
    return v32;
end;
return v12;
