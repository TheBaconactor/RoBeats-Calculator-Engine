-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:48 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v13 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_14 = nil
local v_u_15 = nil
v13:require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15 ]]
    v_u_14 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
end)
local v16 = {}
local v_u_17 = 0
v16.new = function(_, p_u_18, p_u_19, p_u_20) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_5, (copy 6): v_u_9, (copy 7): v_u_10, (copy 8): v_u_11, (copy 9): v_u_8, (copy 10): v_u_12, (ref 11): v_u_17, (ref 12): v_u_14, (copy 13): v_u_6, (ref 14): v_u_15, (copy 15): v_u_7 ]]
    local v21 = v_u_2:new(p_u_19, p_u_20)
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = nil
    v21.cons = function(p_u_25) --[[ Name: cons ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_1, (copy 3): p_u_18, (ref 4): v_u_4, (ref 5): v_u_3, (copy 6): p_u_19, (ref 7): v_u_5, (copy 8): p_u_20, (ref 9): v_u_23, (ref 10): v_u_9, (ref 11): v_u_10, (ref 12): v_u_11, (ref 13): v_u_8, (ref 14): v_u_12, (ref 15): v_u_17, (ref 16): v_u_14, (ref 17): v_u_24, (ref 18): v_u_6, (ref 19): v_u_15 ]]
        v_u_22 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.RobeatsBirthdayEventUI:Clone()
        v_u_22.Name = v_u_1:gen_name(v_u_22.Name)
        p_u_25:set_showing(true)
        p_u_25._native_size = v_u_22.PrimaryPart.Size
        p_u_25._size = p_u_25._native_size
        p_u_25:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_22.PrimaryPart, v_u_22.BackButtonSurface), p_u_19, function() --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): p_u_20, (copy 4): p_u_25 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_MENU_CLOSE)
            p_u_20:remove_menu(p_u_25)
        end))
        local l_LoadedSection_0 = v_u_22.MainSurface.SurfaceGui.Frame.LoadedSection
        local l_SongPageDisplay_0 = l_LoadedSection_0.SongPageDisplay
        local v_u_26 = p_u_25:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_22.PrimaryPart, v_u_22.ArrowLeft), p_u_19, function() --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_23 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_23:prev_page()
        end))
        local v_u_27 = p_u_25:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_22.PrimaryPart, v_u_22.ArrowRight), p_u_19, function() --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_23 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_23:next_page()
        end))
        local v_u_28 = v_u_9:get_birthday_event_playable_song_set():key_list()
        v_u_28:sort(function(p29, p30) --[[ Line: 77 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10:singleton():get_difficulty_for_key(p30) - v_u_10:singleton():get_difficulty_for_key(p29);
        end)
        local v_u_31 = v_u_11:new(p_u_18, v_u_22.SongElementDisplay, v_u_3:new(p_u_25, v_u_22.PrimaryPart, v_u_22.SongElementDisplay.PrimaryPart))
        local l_SongClaimedDisplay_0 = l_LoadedSection_0.SongClaimedDisplay
        v_u_23 = v_u_8:new():set_fn_get_data_list(function() --[[ Line: 89 ]]
            --[[ Upvalues: (copy 1): v_u_28 ]]
            return v_u_28;
        end):set_fn_set_element_data(function(p32, p33) --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): p_u_18, (copy 2): v_u_31, (ref 3): v_u_12, (copy 4): l_SongClaimedDisplay_0 ]]
            p32:display_song(p33)
            p_u_18._bgm_manager:preview_songkey(p33)
            l_SongClaimedDisplay_0.Text = v_u_12:get_song_key_owned_count(p_u_18._player_blob_manager:get_player_blob(), (v_u_31:get_element_data())) > 0 and "You own this song." or "You do not own this song. Play it to get a free copy!"
        end):set_fn_next_prev_visible(function(p34, p35) --[[ Line: 106 ]]
            --[[ Upvalues: (copy 1): v_u_27, (copy 2): v_u_26 ]]
            v_u_27:set_visible(p34)
            v_u_26:set_visible(p35)
        end):set_fn_update_page_display(function(p36, p37) --[[ Line: 110 ]]
            --[[ Upvalues: (copy 1): l_SongPageDisplay_0 ]]
            l_SongPageDisplay_0.Text = string.format("Song %d (of %d)", p36, p37)
        end):set_do_wrap(true):set_i_offset(v_u_17):set_fn_store_i_offset(function(p38) --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = p38
        end)
        v_u_23:push_display_element(v_u_31)
        v_u_23:page_update()
        p_u_25:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_22.PrimaryPart, v_u_22.SongInfoButton), p_u_19, function() --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_11, (copy 4): v_u_31 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_11:show_song_info_popup(p_u_18, v_u_31:get_element_data())
        end))
        local function f_claim_mini_handle_response(p39, p40) --[[ Name: claim_mini_handle_response ]] --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): p_u_19, (ref 5): p_u_20 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            local v_u_41 = p_u_18._menus:push_menu(v_u_14:new(p_u_18, p_u_19, p_u_20):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_18._evt:wait_on_event_once(p40, function(p42, p_u_43) --[[ Line: 141 ]]
                --[[ Upvalues: (ref 1): p_u_18, (copy 2): v_u_41, (ref 3): p_u_20, (ref 4): v_u_14, (ref 5): p_u_19, (ref 6): v_u_5 ]]
                if p42 == true then
                    p_u_18._player_blob_manager:do_sync(function(_) --[[ Line: 148 ]]
                        --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_41, (ref 3): v_u_14, (ref 4): p_u_19, (ref 5): p_u_20, (copy 6): p_u_43, (ref 7): v_u_5 ]]
                        p_u_18._menus:remove_menu(v_u_41)
                        p_u_18._menus:push_menu(v_u_14:new(p_u_18, p_u_19, p_u_20):set_text("Claimed Reward!", p_u_43))
                        p_u_18._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                    end)
                else
                    p_u_18._menus:remove_menu(v_u_41)
                    p_u_20:push_menu(v_u_14:new(p_u_18, p_u_19, p_u_20):set_text("Failed", p_u_43))
                    p_u_18._sfx_manager:play_sfx(v_u_5.SFX_FAIL)
                end;
            end)
            p_u_18._evt:fire_event_to_server(p39)
        end;
        v_u_24 = p_u_25:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_22.PrimaryPart, v_u_22.ClaimButton), p_u_19, function() --[[ Line: 165 ]]
            --[[ Upvalues: (copy 1): f_claim_mini_handle_response, (ref 2): v_u_6 ]]
            f_claim_mini_handle_response(v_u_6.EVT_SpecialEvent_RobeatsBirthdayEventClaim_Client, v_u_6.EVT_SpecialEvent_RobeatsBirthdayEventClaim_Server)
        end))
        v_u_4:button_add_enabled_anim(v_u_24, function() --[[ Line: 172 ]]
            --[[ Upvalues: (copy 1): p_u_25 ]]
            return p_u_25:get_alpha();
        end)
        p_u_25:update_claim_button_status()
        p_u_25:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_22.PrimaryPart, v_u_22.PlayButton), p_u_19, function() --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_9, (ref 4): v_u_15, (copy 5): v_u_31 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
            p_u_18._game_join_protocol:set_event_info(v_u_9.EventMission.RobeatsBirthdayEvent)
            p_u_18._menus:push_menu(v_u_15:new(p_u_18, p_u_18._spui, p_u_18._menus, v_u_31:get_element_data()))
        end))
        p_u_25:transition_update_visual(0)
        p_u_25:layout()
    end;
    v21.update_claim_button_status = function(_) --[[ Name: update_claim_button_status ]] --[[ Line: 194 ]]
        --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_9, (ref 3): v_u_24 ]]
        if v_u_9:test_playerblob_can_claim_song_launch_claimed_id(p_u_18._player_blob_manager:get_player_blob(), v_u_9:get_birthday_event_song_launch_claimed_id()) then
            v_u_24:set_enabled(true)
        else
            v_u_24:set_enabled(false)
        end;
    end;
    v21.on_refocus = function(p44) --[[ Name: on_refocus ]] --[[ Line: 203 ]]
        p44:update_claim_button_status()
    end;
    v21.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 207 ]]
        --[[ Upvalues: (ref 1): v_u_22, (copy 2): p_u_18 ]]
        v_u_22:Destroy()
        p_u_18._bgm_manager:stop_song_preview()
    end;
    v21.behaviour_update = function(p45, p46, _) --[[ Name: behaviour_update ]] --[[ Line: 212 ]]
        --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_23 ]]
        p45:behaviour_update_base(p46, p_u_18)
        for _, v47 in v_u_23:get_display_elements():key_itr() do
            v47:behaviour_update(p46)
        end;
    end;
    local v_u_48 = 1
    local v_u_49 = 1
    v21.layout = function(p50) --[[ Name: layout ]] --[[ Line: 221 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_49, (ref 3): v_u_22, (ref 4): v_u_23 ]]
        p50:opt_rescale_to_max_nxy(p_u_19, 0.8, 0.8, v_u_49)
        local v51, v52 = p50:opt_update_cframe_params(p_u_19, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p50:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v51 == true then
            v_u_22:SetPrimaryPartCFrame(v52)
        end;
        v_u_23:layout()
    end;
    v21.set_alpha = function(_, p53) --[[ Name: set_alpha ]] --[[ Line: 234 ]]
        --[[ Upvalues: (ref 1): v_u_48, (ref 2): v_u_1, (ref 3): v_u_22 ]]
        if v_u_48 ~= p53 then
            v_u_48 = p53
            v_u_1:r_set_alpha(v_u_22, v_u_48)
        end;
    end;
    v21.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 240 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        return v_u_48;
    end;
    v21.set_scale = function(_, p54) --[[ Name: set_scale ]] --[[ Line: 241 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        v_u_49 = p54
    end;
    v21.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 242 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        return v_u_49;
    end;
    v21.get_native_size = function(p55) --[[ Name: get_native_size ]] --[[ Line: 244 ]]
        return p55._native_size;
    end;
    v21.get_size = function(p56) --[[ Name: get_size ]] --[[ Line: 247 ]]
        return p56._size;
    end;
    v21.set_size = function(p57, p58) --[[ Name: set_size ]] --[[ Line: 250 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        p57._size = p58
        v_u_22.PrimaryPart.Size = Vector3.new(p58.X, p58.Y, 0)
    end;
    v21.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 254 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22.PrimaryPart.Position;
    end;
    v21.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 257 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22.PrimaryPart.SurfaceGui;
    end;
    v21.set_showing = function(_, p59) --[[ Name: set_showing ]] --[[ Line: 260 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_7 ]]
        if p59 then
            v_u_22.Parent = v_u_7:get_world_ui_folder()
        else
            v_u_22.Parent = nil
        end;
    end;
    v21:cons()
    return v21;
end;
return v16;
