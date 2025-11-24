-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:40 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Shared.PlayerListActivity)
local v_u_10 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_11 = require(game.ReplicatedStorage.Shared.ListAdapter)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
local v_u_13 = require(game.ReplicatedStorage.Shared.PlayerStatus)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
v14:require_client(function() --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_15 ]]
    v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
end)
local v16 = {}
local v_u_34 = {
    ["new"] = function(_, _, _, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 293 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_9, (copy 3): v_u_6 ]]
        local v_u_20 = {}
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local v_u_29 = 0
        local function f_cons() --[[ Name: cons ]] --[[ Line: 310 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_17, (ref 3): v_u_23, (ref 4): v_u_24, (ref 5): v_u_25, (ref 6): v_u_26, (ref 7): v_u_27, (ref 8): v_u_28, (ref 9): v_u_1, (copy 10): v_u_20 ]]
            v_u_21 = p_u_17:get_child_part().SurfaceGui
            local l_Frame_0 = v_u_21.Frame
            v_u_23 = l_Frame_0.NameDisplay
            v_u_24 = l_Frame_0.SubDisplay
            v_u_25 = l_Frame_0.AlbumArt
            v_u_26 = l_Frame_0.AlbumArt.AlbumArtOverlay
            v_u_27 = l_Frame_0.AlbumArt.DifficultyFrame.DifficultyDisplay
            v_u_28 = l_Frame_0.IconBack.Icon
            v_u_28.Name = v_u_1:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0
            }, "Icon")
            v_u_20:set_display_element(nil)
        end;
        v_u_20.get_player_list_entry = function(_) --[[ Name: get_player_list_entry ]] --[[ Line: 325 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        local v_u_30 = -1
        local function f_update_match_time_display_str() --[[ Name: update_match_time_display_str ]] --[[ Line: 328 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_9, (ref 3): v_u_29, (ref 4): v_u_30, (ref 5): v_u_1, (ref 6): v_u_6, (ref 7): v_u_24 ]]
            if v_u_22 == nil or v_u_22:get_activity() ~= v_u_9.Match then
                v_u_24.Text = ""
            else
                local v31 = math.floor(v_u_29 / 1000)
                if v31 ~= v_u_30 then
                    v_u_24.Text = string.format("In Match (%s)", (string.format("%s / %s", v_u_1:format_ms_time(v_u_29), v_u_1:format_ms_time(v_u_6:singleton():songkey_get_approx_length_sec(v_u_22:get_song_key()) * 1000))))
                    v_u_30 = v31
                    return;
                end;
            end;
        end;
        v_u_20.set_display_element = function(_, p32) --[[ Name: set_display_element ]] --[[ Line: 344 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_22, (ref 3): v_u_21, (copy 4): p_u_18, (copy 5): p_u_19, (ref 6): v_u_23, (ref 7): v_u_1, (ref 8): v_u_24, (ref 9): v_u_25, (ref 10): v_u_9, (ref 11): v_u_29, (copy 12): f_update_match_time_display_str, (ref 13): v_u_6, (ref 14): v_u_26, (ref 15): v_u_27 ]]
            v_u_28.Image = ""
            v_u_22 = p32
            if v_u_22 == nil then
                v_u_21.Enabled = false
                p_u_18:set_visible(false)
                p_u_19:set_visible(false)
            else
                v_u_21.Enabled = true
                v_u_23.Text = v_u_22:get_name()
                v_u_1:get_user_thumbnail(v_u_22:get_player_id(), function(p33, _) --[[ Line: 354 ]]
                    --[[ Upvalues: (ref 1): v_u_28 ]]
                    if v_u_28 ~= nil then
                        v_u_28.Image = p33
                    end;
                end, false)
                if v_u_22:get_player_id() == v_u_1:get_local_userid() then
                    v_u_24.Text = "(You)"
                    p_u_18:set_visible(false)
                    p_u_19:set_visible(false)
                    v_u_25.Visible = false
                elseif v_u_22:get_activity() == v_u_9.Lobby then
                    v_u_24.Text = "In Lobby"
                    p_u_18:set_visible(false)
                    p_u_19:set_visible(false)
                    v_u_25.Visible = false
                elseif v_u_22:get_activity() == v_u_9.Spectate then
                    v_u_24.Text = "Spectating"
                    p_u_18:set_visible(false)
                    p_u_19:set_visible(false)
                    v_u_25.Visible = false
                elseif v_u_22:get_activity() == v_u_9.MatchMaking then
                    v_u_24.Text = "Matchmaking"
                    p_u_18:set_visible(true)
                    p_u_19:set_visible(false)
                    v_u_25.Visible = true
                elseif v_u_22:get_activity() == v_u_9.Match then
                    v_u_29 = v_u_22:get_match_time_ms()
                    f_update_match_time_display_str()
                    p_u_18:set_visible(false)
                    p_u_19:set_visible(true)
                    v_u_25.Visible = true
                elseif v_u_22:get_activity() == v_u_9.Voting then
                    v_u_24.Text = "Voting"
                    p_u_18:set_visible(false)
                    p_u_19:set_visible(false)
                    v_u_25.Visible = false
                elseif v_u_22:get_activity() == v_u_9.MatchEnded then
                    v_u_24.Text = "Match Ended"
                    p_u_18:set_visible(false)
                    p_u_19:set_visible(false)
                    v_u_25.Visible = true
                else
                    v_u_24.Text = "ERROR"
                    p_u_18:set_visible(false)
                    p_u_19:set_visible(false)
                end;
                if v_u_6:singleton():contains_key(v_u_22:get_song_key()) then
                    v_u_6:singleton():render_coverimage_for_key(v_u_25, v_u_26, v_u_22:get_song_key())
                    v_u_27.Text = tostring(v_u_6:singleton():get_difficulty_for_key(v_u_22:get_song_key()))
                end;
            end;
        end;
        v_u_20.update = function(_, _) --[[ Name: update ]] --[[ Line: 415 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_9, (ref 3): v_u_6, (ref 4): v_u_29, (copy 5): f_update_match_time_display_str ]]
            if v_u_22 ~= nil and (v_u_22:get_activity() == v_u_9.Match and v_u_6:singleton():contains_key(v_u_22:get_song_key())) then
                v_u_29 = v_u_22:get_match_time_ms()
                f_update_match_time_display_str()
            end;
        end;
        v_u_20.layout = function(_) --[[ Name: layout ]] --[[ Line: 424 ]]
            --[[ Upvalues: (copy 1): p_u_17 ]]
            p_u_17:layout()
        end;
        f_cons()
        return v_u_20;
    end
}
local v_u_35 = 0
v16.new = function(_, p_u_36, p_u_37, p_u_38) --[[ Name: new ]] --[[ Line: 39 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_8, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): v_u_7, (copy 7): v_u_11, (ref 8): v_u_35, (ref 9): v_u_15, (copy 10): v_u_10, (copy 11): v_u_34, (copy 12): v_u_12, (copy 13): v_u_2, (copy 14): v_u_13 ]]
    local v_u_39 = v_u_3:new(p_u_37, p_u_38)
    local v_u_40 = nil
    local v_u_41 = false
    local v_u_42 = 1
    local v_u_43 = 1
    local v_u_44 = nil
    local v_u_45 = 1
    local v_u_46 = -1
    local function _() --[[ Name: load_data ]] --[[ Line: 52 ]]
        --[[ Upvalues: (copy 1): p_u_36, (ref 2): v_u_45, (ref 3): v_u_41, (ref 4): v_u_44 ]]
        p_u_36._player_status_manager:set_playerlist_info_update_subscribed(true)
        v_u_45 = 1
        p_u_36._player_status_manager:wait_on_next_playerlist_update(function() --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_45, (ref 3): v_u_44 ]]
            if v_u_41 ~= true then
                v_u_45 = 2
                v_u_44:page_update()
            end;
        end)
        v_u_44:page_update()
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_1, (ref 3): v_u_8, (copy 4): v_u_39, (copy 5): p_u_36, (ref 6): v_u_5, (ref 7): v_u_4, (copy 8): p_u_37, (ref 9): v_u_7, (ref 10): v_u_44, (ref 11): v_u_11, (ref 12): v_u_45, (ref 13): v_u_46, (ref 14): v_u_35, (copy 15): p_u_38, (ref 16): v_u_15, (ref 17): v_u_10, (ref 18): v_u_34, (ref 19): v_u_12, (ref 20): v_u_2, (ref 21): v_u_13, (ref 22): v_u_41 ]]
        v_u_40 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.PlayerListUI:Clone()
        v_u_40.Name = v_u_1:gen_name(v_u_40.Name)
        v_u_40.Parent = v_u_8:get_world_ui_folder()
        v_u_39._native_size = v_u_40.PrimaryPart.Size
        v_u_39._size = v_u_39._native_size
        local v_u_47 = v_u_39:add_cycle_element(p_u_36, 1, v_u_5:new(v_u_4:new(v_u_39, v_u_40.PrimaryPart, v_u_40.TopArrowSurface), p_u_37, function() --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (ref 3): v_u_44 ]]
            p_u_36._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_44:prev_page()
        end))
        local v_u_48 = v_u_39:add_cycle_element(p_u_36, 1, v_u_5:new(v_u_4:new(v_u_39, v_u_40.PrimaryPart, v_u_40.BottomArrowSurface), p_u_37, function() --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (ref 3): v_u_44 ]]
            p_u_36._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_44:next_page()
        end))
        local l_CountDisplay_0 = v_u_40.MainSurface.SurfaceGui.Frame.CountDisplay
        local l_PageDisplay_0 = v_u_40.MainSurface.SurfaceGui.Frame.PageDisplay
        v_u_44 = v_u_11:new():set_fn_get_data_list(function() --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): p_u_36 ]]
            return p_u_36._player_status_manager:get_cached_playerlist_info_list();
        end):set_fn_set_element_data(function(p49, p50) --[[ Line: 94 ]]
            if p50 == nil then
                p49:set_display_element(nil)
            else
                p49:set_display_element(p50)
            end;
        end):set_fn_next_prev_visible(function(p51, p52) --[[ Line: 102 ]]
            --[[ Upvalues: (copy 1): v_u_48, (copy 2): v_u_47 ]]
            v_u_48:set_visible(p51)
            v_u_47:set_visible(p52)
        end):set_fn_update_page_display(function(p53, p54) --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_45, (copy 2): l_CountDisplay_0, (copy 3): l_PageDisplay_0, (ref 4): p_u_36, (ref 5): v_u_46 ]]
            if v_u_45 == 1 then
                l_CountDisplay_0.Text = "Loading..."
                l_PageDisplay_0.Text = "Loading..."
            else
                l_CountDisplay_0.Text = string.format("%d", p_u_36._player_status_manager:get_cached_playerlist_info_list():count())
                l_PageDisplay_0.Text = string.format("%d of %d", p53, p54)
                v_u_46 = p_u_36._player_status_manager:get_playerlist_updated_time()
            end;
        end):set_fn_store_i_offset(function(p55) --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            v_u_35 = p55
        end):set_i_offset(v_u_35)
        local l_PlayerElementProto_0 = v_u_40.PlayerElementProto
        l_PlayerElementProto_0.Parent = nil
        v_u_44:create_list_elements_from_anchors_and_proto({
            v_u_40.Anchors.Anchor1,
            v_u_40.Anchors.Anchor2,
            v_u_40.Anchors.Anchor3,
            v_u_40.Anchors.Anchor4,
            v_u_40.Anchors.Anchor5
        }, l_PlayerElementProto_0, v_u_40, function(p56) --[[ Line: 133 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): p_u_36, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): p_u_37, (ref 6): v_u_7, (ref 7): p_u_38, (ref 8): v_u_15, (ref 9): v_u_40, (ref 10): v_u_10, (ref 11): v_u_34 ]]
            local v_u_57 = nil
            local v63 = v_u_34:new(p_u_36, v_u_39, v_u_4:new(v_u_39, v_u_40.PrimaryPart, p56.PrimaryPart), v_u_39:add_cycle_element(p_u_36, 1, v_u_5:new(v_u_4:new(v_u_39, p56.PrimaryPart, p56.JoinButtonProto), p_u_37, function() --[[ Line: 138 ]]
                --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (ref 3): v_u_57, (ref 4): p_u_38, (ref 5): v_u_15, (ref 6): p_u_37 ]]
                p_u_36._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                local v58 = v_u_57:get_player_list_entry()
                if v58 ~= nil then
                    p_u_38:push_menu(v_u_15:new(p_u_36, p_u_37, p_u_38, v58:get_song_key(), v58:get_player_id()))
                end;
            end)), (v_u_39:add_cycle_element(p_u_36, 1, v_u_5:new(v_u_4:new(v_u_39, v_u_40.PrimaryPart, p56.SpectateButtonProto), p_u_37, function() --[[ Line: 156 ]]
                --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (ref 3): v_u_57, (ref 4): p_u_38, (ref 5): v_u_10, (ref 6): p_u_37 ]]
                p_u_36._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                if v_u_57:get_player_list_entry() ~= nil then
                    local v_u_59 = p_u_38:push_menu(v_u_10:new(p_u_36, p_u_37, p_u_38):set_text("Joining Match...", "Please wait..."):set_close_button_visible(false))
                    p_u_36._spectate_manager:try_spectate_userid(v_u_57:get_player_list_entry():get_player_id(), function(p60, p61, p62) --[[ Line: 162 ]]
                        --[[ Upvalues: (ref 1): p_u_38, (copy 2): v_u_59, (ref 3): v_u_10, (ref 4): p_u_36, (ref 5): p_u_37 ]]
                        p_u_38:remove_menu(v_u_59)
                        if p60 ~= true then
                            p_u_38:push_menu(v_u_10:new(p_u_36, p_u_37, p_u_38):set_text("Error", p61))
                        end;
                        p62()
                    end)
                end;
            end))))
            return v63;
        end)
        v_u_12:new(v_u_2:new():push_back_table_list({ v_u_40.FilterElements.ListFilterAll, v_u_40.FilterElements.ListFilterJoin, v_u_40.FilterElements.ListFilterSpectate }), v_u_2:new():push_back_table_list({ v_u_13.PlayerListFilterMode.All, v_u_13.PlayerListFilterMode.Joinable, v_u_13.PlayerListFilterMode.Spectateable }), function(p64) --[[ Line: 187 ]]
            --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_44 ]]
            p_u_36._player_status_manager:set_playerlist_filter_mode(p64)
            v_u_44:page_update()
        end, function() --[[ Line: 191 ]]
            --[[ Upvalues: (ref 1): p_u_36 ]]
            return p_u_36._player_status_manager:get_playerlist_filter_mode();
        end, v_u_39, v_u_40.PrimaryPart, p_u_36, p_u_37)
        v_u_12:new(v_u_2:new():push_back_table_list({ v_u_40.FilterElements.ListFilterTime, v_u_40.FilterElements.ListFilterName }), v_u_2:new():push_back_table_list({ v_u_13.PlayerListOrderMode.Time, v_u_13.PlayerListOrderMode.Alphabetical }), function(p65) --[[ Line: 200 ]]
            --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_44 ]]
            p_u_36._player_status_manager:set_playerlist_order_mode(p65)
            v_u_44:page_update()
        end, function() --[[ Line: 204 ]]
            --[[ Upvalues: (ref 1): p_u_36 ]]
            return p_u_36._player_status_manager:get_playerlist_order_mode();
        end, v_u_39, v_u_40.PrimaryPart, p_u_36, p_u_37)
        v_u_39:add_cycle_element(p_u_36, 1, v_u_5:new(v_u_4:new(v_u_39, v_u_40.PrimaryPart, v_u_40.BackButtonSurface), p_u_37, function() --[[ Line: 213 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_39, (ref 3): v_u_41, (ref 4): p_u_36, (ref 5): v_u_7 ]]
            if p_u_38:contains_menu(v_u_39) then
                v_u_41 = true
                p_u_36._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
                p_u_38:remove_menu(v_u_39)
            end;
        end))
        p_u_36._player_status_manager:set_playerlist_info_update_subscribed(true)
        v_u_45 = 1
        p_u_36._player_status_manager:wait_on_next_playerlist_update(function() --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_45, (ref 3): v_u_44 ]]
            if v_u_41 ~= true then
                v_u_45 = 2
                v_u_44:page_update()
            end;
        end)
        v_u_44:page_update()
        v_u_39:layout()
        v_u_39:set_alpha(0)
    end;
    v_u_39.behaviour_update = function(p66, p67, p68) --[[ Name: behaviour_update ]] --[[ Line: 228 ]]
        --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_46, (copy 3): p_u_36, (ref 4): v_u_44 ]]
        p66:behaviour_update_base(p67, p68)
        if p66:is_current_mode_open() then
            if v_u_45 == 2 and v_u_46 ~= p_u_36._player_status_manager:get_playerlist_updated_time() then
                v_u_44:page_update()
            end;
            for _, v69 in v_u_44:get_display_elements():key_itr() do
                v69:update(p67)
            end;
        end;
    end;
    v_u_39.on_refocus = function(_) --[[ Name: on_refocus ]] --[[ Line: 243 ]]
        --[[ Upvalues: (copy 1): p_u_36, (ref 2): v_u_45, (ref 3): v_u_41, (ref 4): v_u_44 ]]
        p_u_36._player_status_manager:set_playerlist_info_update_subscribed(true)
        v_u_45 = 1
        p_u_36._player_status_manager:wait_on_next_playerlist_update(function() --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_45, (ref 3): v_u_44 ]]
            if v_u_41 ~= true then
                v_u_45 = 2
                v_u_44:page_update()
            end;
        end)
        v_u_44:page_update()
    end;
    v_u_39.layout = function(p70) --[[ Name: layout ]] --[[ Line: 247 ]]
        --[[ Upvalues: (copy 1): p_u_37, (ref 2): v_u_43, (ref 3): v_u_40, (ref 4): v_u_44 ]]
        p_u_37:uiobj_rescale_to_max_nxy(p70, 0.5, 0.8, v_u_43)
        v_u_40:SetPrimaryPartCFrame(p_u_37:get_cframe({
            ["PositionNXY"] = Vector2.new(0.925, 0.5),
            ["OffsetXYZ"] = p70:anchored_offset(1, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        v_u_44:layout()
    end;
    v_u_39.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 257 ]]
        --[[ Upvalues: (copy 1): p_u_36, (ref 2): v_u_40 ]]
        p_u_36._player_status_manager:set_playerlist_info_update_subscribed(false)
        v_u_40:Destroy()
    end;
    v_u_39.set_alpha = function(_, p71) --[[ Name: set_alpha ]] --[[ Line: 262 ]]
        --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_1, (ref 3): v_u_40 ]]
        if v_u_42 ~= p71 then
            v_u_42 = p71
            v_u_1:r_set_alpha(v_u_40, v_u_42)
        end;
    end;
    v_u_39.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 268 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        return v_u_42;
    end;
    v_u_39.set_scale = function(_, p72) --[[ Name: set_scale ]] --[[ Line: 269 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        v_u_43 = p72
    end;
    v_u_39.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 270 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        return v_u_43;
    end;
    v_u_39.get_native_size = function(p73) --[[ Name: get_native_size ]] --[[ Line: 272 ]]
        return p73._native_size;
    end;
    v_u_39.get_size = function(p74) --[[ Name: get_size ]] --[[ Line: 275 ]]
        return p74._size;
    end;
    v_u_39.set_size = function(p75, p76) --[[ Name: set_size ]] --[[ Line: 278 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        p75._size = p76
        v_u_40.PrimaryPart.Size = Vector3.new(p76.X, p76.Y, 0)
    end;
    v_u_39.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 282 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        return v_u_40.PrimaryPart.Position;
    end;
    v_u_39.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 285 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        return v_u_40.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_39;
end;
return v16;
