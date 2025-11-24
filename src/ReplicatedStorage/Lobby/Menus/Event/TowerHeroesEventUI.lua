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
    v21.cons = function(p_u_24) --[[ Name: cons ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_1, (copy 3): p_u_18, (ref 4): v_u_4, (ref 5): v_u_3, (copy 6): p_u_19, (ref 7): v_u_5, (copy 8): p_u_20, (ref 9): v_u_23, (ref 10): v_u_9, (ref 11): v_u_10, (ref 12): v_u_11, (ref 13): v_u_8, (ref 14): v_u_12, (ref 15): v_u_17, (ref 16): v_u_14, (ref 17): v_u_6, (ref 18): v_u_15 ]]
        v_u_22 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.TowerHeroesEventUI:Clone()
        v_u_22.Name = v_u_1:gen_name(v_u_22.Name)
        p_u_24:set_showing(true)
        p_u_24._native_size = v_u_22.PrimaryPart.Size
        p_u_24._size = p_u_24._native_size
        p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.BackButtonSurface), p_u_19, function() --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): p_u_20, (copy 4): p_u_24 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_MENU_CLOSE)
            p_u_20:remove_menu(p_u_24)
        end))
        local l_LoadedSection_0 = v_u_22.MainSurface.SurfaceGui.Frame.LoadedSection
        local l_SongPageDisplay_0 = l_LoadedSection_0.SongPageDisplay
        local v_u_25 = p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.ArrowLeft), p_u_19, function() --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_23 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_23:prev_page()
        end))
        local v_u_26 = p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.ArrowRight), p_u_19, function() --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_23 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_23:next_page()
        end))
        local v_u_27 = v_u_9:tower_heroes_get_playable_song_set():key_list()
        v_u_27:sort(function(p28, p29) --[[ Line: 76 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10:singleton():get_difficulty_for_key(p29) - v_u_10:singleton():get_difficulty_for_key(p28);
        end)
        local l_SongClaimedDisplay_0 = l_LoadedSection_0.SongClaimedDisplay
        local v_u_30 = v_u_11:new(p_u_18, v_u_22.SongElementDisplay, v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.SongElementDisplay.PrimaryPart))
        v_u_23 = v_u_8:new():set_fn_get_data_list(function() --[[ Line: 88 ]]
            --[[ Upvalues: (copy 1): v_u_27 ]]
            return v_u_27;
        end):set_fn_set_element_data(function(p31, p32) --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): p_u_18, (copy 2): v_u_30, (ref 3): v_u_9, (ref 4): v_u_12, (copy 5): l_SongClaimedDisplay_0 ]]
            p31:display_song(p32)
            p_u_18._bgm_manager:preview_songkey(p32)
            local v33 = p_u_18._player_blob_manager:get_player_blob()
            local v34, v35 = v_u_9:tower_heroes_get_songkey_grant_target_songkey((v_u_30:get_element_data()))
            l_SongClaimedDisplay_0.Text = (v34 and v_u_12:get_song_key_owned_count(v33, v35) > 0 and "You own the Normal Mode of this song." or "You do not own the Normal Mode of this song.") .. "\n" .. string.format("Claimed %d of %d Normal Mode songs.", v_u_9:tower_heroes_playerblob_get_claim_song_count(v33), v_u_9:tower_heroes_get_claim_song_set():count())
        end):set_fn_next_prev_visible(function(p36, p37) --[[ Line: 110 ]]
            --[[ Upvalues: (copy 1): v_u_26, (copy 2): v_u_25 ]]
            v_u_26:set_visible(p36)
            v_u_25:set_visible(p37)
        end):set_fn_update_page_display(function(p38, p39) --[[ Line: 114 ]]
            --[[ Upvalues: (copy 1): l_SongPageDisplay_0 ]]
            l_SongPageDisplay_0.Text = string.format("Song %d (of %d)", p38, p39)
        end):set_do_wrap(true):set_i_offset(v_u_17):set_fn_store_i_offset(function(p40) --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = p40
        end)
        v_u_23:push_display_element(v_u_30)
        v_u_23:page_update()
        p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.SongInfoButton), p_u_19, function() --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_11, (copy 4): v_u_30 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_11:show_song_info_popup(p_u_18, v_u_30:get_element_data())
        end))
        p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.Mini1InfoButton), p_u_19, function() --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_9 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            p_u_18._menus:push_menu(v_u_14:new(p_u_18, p_u_18._spui, p_u_18._menus):set_text("Claim \'Tower Heroes Wizard\' Mini", string.format("Acquire all %d event Songs to claim the \'Tower Heroes: Wizard\' Mini. Playing the Easy, Normal or Hard mode of the song will grant you the Normal mode (if you do not already own a copy). Claiming the Mini will also grant a badge which will allow you to claim a DJ Hiku Follower and Sticker in \'Tower Heroes\'.", v_u_9:tower_heroes_get_claim_song_set():count())))
        end))
        p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.Mini2InfoButton), p_u_19, function() --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_9 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            p_u_18._menus:push_menu(v_u_14:new(p_u_18, p_u_18._spui, p_u_18._menus):set_text("Claim \'Tower Heroes Mirai\' Mini", string.format("You can claim this Mini when you have both:\n-Claimed all %d Event Normal mode songs\n-Beaten the stage \'Idol Encore\' on Challenge Mode [Easy] in Tower Heroes and earned the badge.", v_u_9:tower_heroes_get_claim_song_set():count())))
        end))
        local function f_claim_mini_handle_response(p41, p42) --[[ Name: claim_mini_handle_response ]] --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): p_u_19, (ref 5): p_u_20 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            local v_u_43 = p_u_18._menus:push_menu(v_u_14:new(p_u_18, p_u_19, p_u_20):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_18._evt:wait_on_event_once(p42, function(p44, p_u_45) --[[ Line: 180 ]]
                --[[ Upvalues: (ref 1): p_u_18, (copy 2): v_u_43, (ref 3): p_u_20, (ref 4): v_u_14, (ref 5): p_u_19, (ref 6): v_u_5 ]]
                if p44 == true then
                    p_u_18._player_blob_manager:do_sync(function(_) --[[ Line: 187 ]]
                        --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_43, (ref 3): v_u_14, (ref 4): p_u_19, (ref 5): p_u_20, (copy 6): p_u_45, (ref 7): v_u_5 ]]
                        p_u_18._menus:remove_menu(v_u_43)
                        p_u_18._menus:push_menu(v_u_14:new(p_u_18, p_u_19, p_u_20):set_text("Claimed Reward!", p_u_45))
                        p_u_18._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                    end)
                else
                    p_u_18._menus:remove_menu(v_u_43)
                    p_u_20:push_menu(v_u_14:new(p_u_18, p_u_19, p_u_20):set_text("Failed", p_u_45))
                    p_u_18._sfx_manager:play_sfx(v_u_5.SFX_FAIL)
                end;
            end)
            p_u_18._evt:fire_event_to_server(p41)
        end;
        p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.ClaimMini1Button), p_u_19, function() --[[ Line: 204 ]]
            --[[ Upvalues: (copy 1): f_claim_mini_handle_response, (ref 2): v_u_6 ]]
            f_claim_mini_handle_response(v_u_6.EVT_SpecialEvent_TowerHeroesClaimMini1_Client, v_u_6.EVT_SpecialEvent_TowerHeroesClaimMini1_Server)
        end))
        p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.ClaimMini2Button), p_u_19, function() --[[ Line: 215 ]]
            --[[ Upvalues: (copy 1): f_claim_mini_handle_response, (ref 2): v_u_6 ]]
            f_claim_mini_handle_response(v_u_6.EVT_SpecialEvent_TowerHeroesClaimMini2_Client, v_u_6.EVT_SpecialEvent_TowerHeroesClaimMini2_Server)
        end))
        p_u_24:add_cycle_element(p_u_18, 1, v_u_4:new(v_u_3:new(p_u_24, v_u_22.PrimaryPart, v_u_22.PlayButton), p_u_19, function() --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_5, (ref 3): v_u_9, (ref 4): v_u_15, (copy 5): v_u_30 ]]
            p_u_18._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
            p_u_18._game_join_protocol:set_event_info(v_u_9.EventMission.TowerHeroesEvent)
            p_u_18._menus:push_menu(v_u_15:new(p_u_18, p_u_18._spui, p_u_18._menus, v_u_30:get_element_data()))
        end))
        p_u_24:transition_update_visual(0)
        p_u_24:layout()
    end;
    v21.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 242 ]]
        --[[ Upvalues: (ref 1): v_u_22, (copy 2): p_u_18 ]]
        v_u_22:Destroy()
        p_u_18._bgm_manager:stop_song_preview()
    end;
    v21.behaviour_update = function(p46, p47, _) --[[ Name: behaviour_update ]] --[[ Line: 247 ]]
        --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_23 ]]
        p46:behaviour_update_base(p47, p_u_18)
        for _, v48 in v_u_23:get_display_elements():key_itr() do
            v48:behaviour_update(p47)
        end;
    end;
    local v_u_49 = 1
    local v_u_50 = 1
    v21.layout = function(p51) --[[ Name: layout ]] --[[ Line: 256 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_50, (ref 3): v_u_22, (ref 4): v_u_23 ]]
        p51:opt_rescale_to_max_nxy(p_u_19, 0.8, 0.8, v_u_50)
        local v52, v53 = p51:opt_update_cframe_params(p_u_19, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p51:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v52 == true then
            v_u_22:SetPrimaryPartCFrame(v53)
        end;
        v_u_23:layout()
    end;
    v21.set_alpha = function(_, p54) --[[ Name: set_alpha ]] --[[ Line: 269 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_1, (ref 3): v_u_22 ]]
        if v_u_49 ~= p54 then
            v_u_49 = p54
            v_u_1:r_set_alpha(v_u_22, v_u_49)
        end;
    end;
    v21.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 275 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        return v_u_49;
    end;
    v21.set_scale = function(_, p55) --[[ Name: set_scale ]] --[[ Line: 276 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        v_u_50 = p55
    end;
    v21.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 277 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        return v_u_50;
    end;
    v21.get_native_size = function(p56) --[[ Name: get_native_size ]] --[[ Line: 279 ]]
        return p56._native_size;
    end;
    v21.get_size = function(p57) --[[ Name: get_size ]] --[[ Line: 282 ]]
        return p57._size;
    end;
    v21.set_size = function(p58, p59) --[[ Name: set_size ]] --[[ Line: 285 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        p58._size = p59
        v_u_22.PrimaryPart.Size = Vector3.new(p59.X, p59.Y, 0)
    end;
    v21.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 289 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22.PrimaryPart.Position;
    end;
    v21.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 292 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22.PrimaryPart.SurfaceGui;
    end;
    v21.set_showing = function(_, p60) --[[ Name: set_showing ]] --[[ Line: 295 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_7 ]]
        if p60 then
            v_u_22.Parent = v_u_7:get_world_ui_folder()
        else
            v_u_22.Parent = nil
        end;
    end;
    v21:cons()
    return v21;
end;
return v16;
