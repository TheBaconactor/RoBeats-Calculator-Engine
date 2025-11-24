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
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistEventInfo)
local v13 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
v13:require_client(function() --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_16, (ref 4): v_u_17, (ref 5): v_u_18 ]]
    v_u_14 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
    v_u_17 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
end)
local v19 = {}
local v_u_20 = 0
v19.new = function(_, p_u_21, p_u_22, p_u_23) --[[ Name: new ]] --[[ Line: 41 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_12, (copy 6): v_u_9, (copy 7): v_u_10, (copy 8): v_u_8, (ref 9): v_u_20, (copy 10): v_u_11, (ref 11): v_u_15, (ref 12): v_u_14, (copy 13): v_u_6, (copy 14): v_u_1, (copy 15): v_u_7 ]]
    local v_u_24 = v_u_2:new(p_u_22, p_u_23)
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_25, (copy 2): v_u_24, (ref 3): v_u_27, (copy 4): p_u_21, (ref 5): v_u_4, (ref 6): v_u_3, (copy 7): p_u_22, (ref 8): v_u_5, (copy 9): p_u_23, (ref 10): v_u_26, (ref 11): v_u_12, (ref 12): v_u_9, (ref 13): v_u_10, (ref 14): v_u_8, (ref 15): v_u_20, (ref 16): v_u_11, (ref 17): v_u_15, (ref 18): v_u_14, (ref 19): v_u_6 ]]
        v_u_25 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.GenericArtistEventUI:Clone()
        v_u_24:set_showing(true)
        v_u_27 = p_u_21._bgm_manager:begin_preview_songkey()
        v_u_24._native_size = v_u_25.PrimaryPart.Size
        v_u_24._size = v_u_24._native_size
        v_u_24:add_cycle_element(p_u_21, 1, v_u_4:new(v_u_3:new(v_u_24, v_u_25.PrimaryPart, v_u_25.BackButtonSurface), p_u_22, function() --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_5, (ref 3): p_u_23, (ref 4): v_u_24 ]]
            p_u_21._sfx_manager:play_sfx(v_u_5.SFX_MENU_CLOSE)
            p_u_23:remove_menu(v_u_24)
        end))
        local l_SongPageDisplay_0 = v_u_25.MainSurface.SurfaceGui.Frame.LoadedSection.SongPageDisplay
        local v_u_28 = v_u_24:add_cycle_element(p_u_21, 1, v_u_4:new(v_u_3:new(v_u_24, v_u_25.PrimaryPart, v_u_25.ArrowLeft), p_u_22, function() --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_5, (ref 3): v_u_26 ]]
            p_u_21._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_26:prev_page()
        end))
        local v_u_29 = v_u_24:add_cycle_element(p_u_21, 1, v_u_4:new(v_u_3:new(v_u_24, v_u_25.PrimaryPart, v_u_25.ArrowRight), p_u_22, function() --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_5, (ref 3): v_u_26 ]]
            p_u_21._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_26:next_page()
        end))
        local v_u_30 = v_u_12:get_playable_song_set():key_list()
        v_u_30:sort(function(p31, p32) --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9:singleton():get_difficulty_for_key(p32) - v_u_9:singleton():get_difficulty_for_key(p31);
        end)
        local v_u_33 = v_u_10:new(p_u_21, v_u_25.SongElementDisplay, v_u_3:new(v_u_24, v_u_25.PrimaryPart, v_u_25.SongElementDisplay.PrimaryPart))
        v_u_26 = v_u_8:new():set_fn_get_data_list(function() --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): v_u_30 ]]
            return v_u_30;
        end):set_fn_set_element_data(function(p34, p35) --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): p_u_21 ]]
            p34:display_song(p35)
            p_u_21._bgm_manager:preview_songkey(p35)
        end):set_fn_next_prev_visible(function(p36, p37) --[[ Line: 126 ]]
            --[[ Upvalues: (copy 1): v_u_29, (copy 2): v_u_28 ]]
            v_u_29:set_visible(p36)
            v_u_28:set_visible(p37)
        end):set_fn_update_page_display(function(p38, p39) --[[ Line: 130 ]]
            --[[ Upvalues: (copy 1): l_SongPageDisplay_0 ]]
            l_SongPageDisplay_0.Text = string.format("Song %d (of %d)", p38, p39)
        end):set_do_wrap(true):set_i_offset(v_u_20):set_fn_store_i_offset(function(p40) --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            v_u_20 = p40
        end)
        v_u_26:push_display_element(v_u_33)
        v_u_26:page_update()
        v_u_24:add_cycle_element(p_u_21, 1, v_u_4:new(v_u_3:new(v_u_24, v_u_25.PrimaryPart, v_u_25.SongInfoButton), p_u_22, function() --[[ Line: 145 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_5, (copy 3): v_u_33, (ref 4): v_u_10 ]]
            p_u_21._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_10:show_song_info_popup(p_u_21, v_u_33:get_element_data(), nil, "")
        end))
        v_u_24:add_cycle_element(p_u_21, 1, v_u_4:new(v_u_3:new(v_u_24, v_u_25.PrimaryPart, v_u_25.PlayButton), p_u_22, function() --[[ Line: 247 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_5, (ref 3): v_u_11, (ref 4): v_u_15, (copy 5): v_u_33 ]]
            p_u_21._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
            p_u_21._game_join_protocol:set_event_info(v_u_11.EventMission.GenericArtistEvent)
            p_u_21._menus:push_menu(v_u_15:new(p_u_21, p_u_21._spui, p_u_21._menus, v_u_33:get_element_data()))
        end))
        local v41 = v_u_25:FindFirstChild("ButtonA")
        if v41 then
            v41.Parent = nil
        end;
        local v42 = v_u_25:FindFirstChild("ButtonB")
        if v42 then
            v_u_24:add_cycle_element(p_u_21, 1, v_u_4:new(v_u_3:new(v_u_24, v_u_25.PrimaryPart, v42), p_u_22, function() --[[ Line: 288 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): p_u_22, (ref 5): p_u_23, (ref 6): v_u_6 ]]
                p_u_21._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
                p_u_21._menus:push_menu(v_u_14:new(p_u_21, p_u_22, p_u_23):set_text("Confirm", "Teleport to Super League Arcade?"):set_okay_button_fn(function() --[[ Line: 294 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_14, (ref 3): p_u_22, (ref 4): p_u_23, (ref 5): v_u_6 ]]
                    p_u_21._menus:push_menu(v_u_14:new(p_u_21, p_u_22, p_u_23):set_text("Loading...", "Please wait..."))
                    p_u_21._evt:fire_event_to_server(v_u_6.EVT_SpecialEvent_GenericArtistTeleport_Client)
                end))
            end))
        end;
        v_u_24:transition_update_visual(0)
        v_u_24:layout()
    end;
    v_u_24.on_refocus = function(_) end;
    v_u_24.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 339 ]]
        --[[ Upvalues: (ref 1): v_u_25, (copy 2): p_u_21, (ref 3): v_u_27 ]]
        v_u_25:Destroy()
        p_u_21._bgm_manager:stop_song_preview(v_u_27)
    end;
    v_u_24.behaviour_update = function(p43, p44, _) --[[ Name: behaviour_update ]] --[[ Line: 344 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_26 ]]
        p43:behaviour_update_base(p44, p_u_21)
        for _, v45 in v_u_26:get_display_elements():key_itr() do
            v45:behaviour_update(p44)
        end;
    end;
    local v_u_46 = 1
    local v_u_47 = 1
    v_u_24.layout = function(p48) --[[ Name: layout ]] --[[ Line: 353 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_47, (ref 3): v_u_25, (ref 4): v_u_26 ]]
        p48:opt_rescale_to_max_nxy(p_u_22, 0.8, 0.8, v_u_47)
        local v49, v50 = p48:opt_update_cframe_params(p_u_22, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p48:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v49 == true then
            v_u_25:SetPrimaryPartCFrame(v50)
        end;
        v_u_26:layout()
    end;
    v_u_24.set_alpha = function(_, p51) --[[ Name: set_alpha ]] --[[ Line: 366 ]]
        --[[ Upvalues: (ref 1): v_u_46, (ref 2): v_u_1, (ref 3): v_u_25 ]]
        if v_u_46 ~= p51 then
            v_u_46 = p51
            v_u_1:r_set_alpha(v_u_25, v_u_46)
        end;
    end;
    v_u_24.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 372 ]]
        --[[ Upvalues: (ref 1): v_u_46 ]]
        return v_u_46;
    end;
    v_u_24.set_scale = function(_, p52) --[[ Name: set_scale ]] --[[ Line: 373 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        v_u_47 = p52
    end;
    v_u_24.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 374 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        return v_u_47;
    end;
    v_u_24.get_native_size = function(p53) --[[ Name: get_native_size ]] --[[ Line: 376 ]]
        return p53._native_size;
    end;
    v_u_24.get_size = function(p54) --[[ Name: get_size ]] --[[ Line: 379 ]]
        return p54._size;
    end;
    v_u_24.set_size = function(p55, p56) --[[ Name: set_size ]] --[[ Line: 382 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        p55._size = p56
        v_u_25.PrimaryPart.Size = Vector3.new(p56.X, p56.Y, 0)
    end;
    v_u_24.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 386 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25.PrimaryPart.Position;
    end;
    v_u_24.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 389 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25.PrimaryPart.SurfaceGui;
    end;
    v_u_24.set_showing = function(_, p57) --[[ Name: set_showing ]] --[[ Line: 392 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_7 ]]
        if p57 then
            v_u_25.Parent = v_u_7:get_world_ui_folder()
        else
            v_u_25.Parent = nil
        end;
    end;
    f_cons()
    return v_u_24;
end;
return v19;
