-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:48 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_13 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
v14:require_client(function() --[[ Line: 24 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): v_u_17 ]]
    v_u_15 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.PlayUI)
end)
local v18 = {}
local v_u_24 = {
    ["new"] = function(_, p_u_19, _, _, _, p_u_20) --[[ Name: new ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_10 ]]
        local v21 = {
            ["behaviour_update"] = function(_, _) end,
            ["layout"] = function(_) end
        }
        local v_u_22 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_22, (copy 2): p_u_20, (copy 3): p_u_19, (ref 4): v_u_10 ]]
            v_u_22 = p_u_20.MainSurface.SurfaceGui.Frame.Page1Section
            if v_u_10:get_24kgoldn_playerblob_has_claimed_pet((p_u_19._player_blob_manager:get_player_blob())) then
                v_u_22.FoundCountDisplay.Text = "You\'ve found all 10 Golden Microphones!"
            else
                v_u_22.FoundCountDisplay.Text = string.format("Found %d of 10 Golden Microphones.", v_u_10:get_24kgoldn_claimed_hunt_ids_set():count())
            end;
        end;
        v21.set_visible = function(_, p23) --[[ Name: set_visible ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22.Visible = p23
        end;
        f_cons()
        return v21;
    end
}
local v_u_25 = 0
local v_u_51 = {
    ["new"] = function(_, p_u_26, p_u_27, _, p_u_28, p_u_29) --[[ Name: new ]] --[[ Line: 68 ]]
        --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_13, (copy 3): v_u_6, (copy 4): v_u_5, (copy 5): v_u_7, (copy 6): v_u_11, (copy 7): v_u_12, (copy 8): v_u_9, (ref 9): v_u_25, (ref 10): v_u_16 ]]
        local v30 = {}
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): v_u_31, (copy 2): p_u_29, (ref 3): v_u_10, (copy 4): p_u_26, (ref 5): v_u_13, (ref 6): v_u_34, (copy 7): p_u_28, (ref 8): v_u_6, (ref 9): v_u_5, (copy 10): p_u_27, (ref 11): v_u_7, (ref 12): v_u_32, (ref 13): v_u_33, (ref 14): v_u_11, (ref 15): v_u_35, (ref 16): v_u_12, (ref 17): v_u_9, (ref 18): v_u_25, (ref 19): v_u_37, (ref 20): v_u_36, (ref 21): v_u_16 ]]
            v_u_31 = p_u_29.MainSurface.SurfaceGui.Frame.Page2Section
            v_u_31.PlayCountDisplay.Text = string.format("Play Count: %d", v_u_10:get_24kgoldn_playcount())
            local v38 = p_u_26._player_blob_manager:get_player_blob()
            if v_u_10:get_24kgoldn_playerblob_has_claimed_gear(v38) then
                v_u_31.GearInfoDisplay.Text = "You\'ve claimed this gear."
            elseif v_u_13:playerblob_can_add_more_gear(v38) then
                v_u_31.GearInfoDisplay.Text = "Play this song from this menu to get the gear!"
            else
                v_u_31.GearInfoDisplay.Text = "You cannot add any more gear. Please trash one of your gear to get this gear"
            end;
            local l_SongPageDisplay_0 = v_u_31.SongPageDisplay
            v_u_34 = p_u_28:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_28, p_u_29.PrimaryPart, p_u_29.ArrowLeft), p_u_27, function() --[[ Line: 94 ]]
                --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_7, (ref 3): v_u_32 ]]
                p_u_26._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_32:prev_page()
            end))
            v_u_33 = p_u_28:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_28, p_u_29.PrimaryPart, p_u_29.ArrowRight), p_u_27, function() --[[ Line: 103 ]]
                --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_7, (ref 3): v_u_32 ]]
                p_u_26._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_32:next_page()
            end))
            local v_u_39 = v_u_10:get_24kgoldn_event_playable_song_set():key_list()
            v_u_39:sort(function(p40, p41) --[[ Line: 110 ]]
                --[[ Upvalues: (ref 1): v_u_11 ]]
                return v_u_11:singleton():get_difficulty_for_key(p41) - v_u_11:singleton():get_difficulty_for_key(p40);
            end)
            v_u_35 = v_u_12:new(p_u_26, p_u_29.SongElementDisplay, v_u_5:new(p_u_28, p_u_29.PrimaryPart, p_u_29.SongElementDisplay.PrimaryPart))
            v_u_32 = v_u_9:new():set_fn_get_data_list(function() --[[ Line: 121 ]]
                --[[ Upvalues: (copy 1): v_u_39 ]]
                return v_u_39;
            end):set_fn_set_element_data(function(p42, p43) --[[ Line: 124 ]]
                --[[ Upvalues: (ref 1): p_u_26 ]]
                p42:display_song(p43)
                p_u_26._bgm_manager:preview_songkey(p43)
            end):set_fn_next_prev_visible(function(p44, p45) --[[ Line: 128 ]]
                --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_34 ]]
                v_u_33:set_visible(p44)
                v_u_34:set_visible(p45)
            end):set_fn_update_page_display(function(p46, p47) --[[ Line: 132 ]]
                --[[ Upvalues: (copy 1): l_SongPageDisplay_0 ]]
                l_SongPageDisplay_0.Text = string.format("Song %d (of %d)", p46, p47)
            end):set_do_wrap(true):set_i_offset(v_u_25):set_fn_store_i_offset(function(p48) --[[ Line: 137 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                v_u_25 = p48
            end)
            v_u_32:push_display_element(v_u_35)
            v_u_32:page_update()
            v_u_37 = p_u_28:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_28, p_u_29.PrimaryPart, p_u_29.SongInfoButton), p_u_27, function() --[[ Line: 147 ]]
                --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_7, (ref 3): v_u_12, (ref 4): v_u_35 ]]
                p_u_26._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_12:show_song_info_popup(p_u_26, v_u_35:get_element_data())
            end))
            v_u_36 = p_u_28:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_28, p_u_29.PrimaryPart, p_u_29.PlaySongButton), p_u_27, function() --[[ Line: 159 ]]
                --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_7, (ref 3): v_u_10, (ref 4): v_u_16, (ref 5): v_u_35 ]]
                p_u_26._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                p_u_26._game_join_protocol:set_event_info(v_u_10.EventMission.GoldnEvent)
                p_u_26._menus:push_menu(v_u_16:new(p_u_26, p_u_26._spui, p_u_26._menus, v_u_35:get_element_data()))
            end))
        end;
        v30.behaviour_update = function(_, p49) --[[ Name: behaviour_update ]] --[[ Line: 172 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            v_u_35:behaviour_update(p49)
        end;
        v30.layout = function(_) --[[ Name: layout ]] --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            v_u_32:layout()
        end;
        v30.set_visible = function(_, p50) --[[ Name: set_visible ]] --[[ Line: 180 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_33, (ref 3): v_u_34, (ref 4): v_u_35, (ref 5): v_u_36, (ref 6): v_u_37 ]]
            v_u_31.Visible = p50
            v_u_33:set_visible(p50)
            v_u_34:set_visible(p50)
            v_u_35:set_visible(p50)
            v_u_36:set_visible(p50)
            v_u_37:set_visible(p50)
        end;
        f_cons()
        return v30;
    end
}
local v_u_65 = {
    ["new"] = function(_, p_u_52, p_u_53, p_u_54, p_u_55, p_u_56) --[[ Name: new ]] --[[ Line: 194 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_5, (copy 3): v_u_7, (ref 4): v_u_16, (ref 5): v_u_17, (copy 6): v_u_10 ]]
        local v57 = {
            ["behaviour_update"] = function(_, _) end,
            ["layout"] = function(_) end
        }
        local v_u_58 = nil
        local v_u_59 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 200 ]]
            --[[ Upvalues: (ref 1): v_u_58, (copy 2): p_u_56, (ref 3): v_u_59, (copy 4): p_u_55, (copy 5): p_u_52, (ref 6): v_u_6, (ref 7): v_u_5, (copy 8): p_u_53, (ref 9): v_u_7, (ref 10): v_u_16, (copy 11): p_u_54, (ref 12): v_u_17, (ref 13): v_u_10 ]]
            v_u_58 = p_u_56.MainSurface.SurfaceGui.Frame.Page3Section
            v_u_59 = p_u_55:add_cycle_element(p_u_52, 1, v_u_6:new(v_u_5:new(p_u_55, p_u_56.PrimaryPart, p_u_56.PlayMenuButton), p_u_53, function() --[[ Line: 206 ]]
                --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_7, (ref 3): v_u_16, (ref 4): p_u_54, (ref 5): v_u_17, (ref 6): p_u_53 ]]
                p_u_52._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                v_u_16:set_auto_equip_best_loadout(false)
                p_u_54:push_menu(v_u_17:new(p_u_52, p_u_53, p_u_54))
            end))
            v_u_6:button_add_enabled_anim(v_u_59, function() --[[ Line: 212 ]]
                --[[ Upvalues: (ref 1): p_u_55 ]]
                return p_u_55:get_alpha();
            end)
            local v60 = p_u_52._player_blob_manager:get_player_blob()
            if v_u_10:is_24kgoldn_gear_equipped(v60) then
                v_u_58.GearEquippedDisplay.Visible = true
                v_u_58.GearEquippedText.Text = "Equipped"
            else
                v_u_58.GearEquippedDisplay.Visible = false
                v_u_58.GearEquippedText.Text = "Not Equipped"
            end;
            if v_u_10:is_24kgoldn_pet_equipped(v60) then
                v_u_58.MiniEquippedDisplay.Visible = true
                v_u_58.MiniEquippedText.Text = "Equipped"
            else
                v_u_58.MiniEquippedDisplay.Visible = false
                v_u_58.MiniEquippedText.Text = "Not Equipped"
            end;
        end;
        v57.set_visible = function(_, p61) --[[ Name: set_visible ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_58, (ref 2): v_u_59, (copy 3): p_u_52, (ref 4): v_u_10 ]]
            v_u_58.Visible = p61
            v_u_59:set_visible(p61)
            if p61 then
                local v62 = p_u_52._player_blob_manager:get_player_blob()
                local v63 = v_u_59
                local v64 = v_u_10:is_24kgoldn_gear_equipped(v62)
                if v64 then
                    v64 = v_u_10:is_24kgoldn_pet_equipped(v62)
                end;
                v63:set_enabled(v64)
            end;
        end;
        f_cons()
        return v57;
    end
}
local v_u_66 = 1
v18.new = function(_, p_u_67, p_u_68, p_u_69) --[[ Name: new ]] --[[ Line: 251 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_2, (ref 4): v_u_66, (copy 5): v_u_1, (copy 6): v_u_6, (copy 7): v_u_5, (copy 8): v_u_7, (copy 9): v_u_24, (copy 10): v_u_51, (copy 11): v_u_65, (copy 12): v_u_10, (copy 13): v_u_8 ]]
    local v70 = v_u_4:new(p_u_68, p_u_69)
    local v_u_71 = nil
    local v_u_72 = v_u_3:new()
    local v_u_73 = v_u_2:new()
    local function _() --[[ Name: get_active_page ]] --[[ Line: 257 ]]
        --[[ Upvalues: (copy 1): v_u_72, (ref 2): v_u_66 ]]
        return v_u_72:get(v_u_66);
    end;
    v70.cons = function(p_u_74) --[[ Name: cons ]] --[[ Line: 259 ]]
        --[[ Upvalues: (ref 1): v_u_71, (ref 2): v_u_1, (copy 3): p_u_67, (ref 4): v_u_6, (ref 5): v_u_5, (copy 6): p_u_68, (ref 7): v_u_7, (copy 8): p_u_69, (copy 9): v_u_72, (ref 10): v_u_24, (ref 11): v_u_51, (ref 12): v_u_65, (ref 13): v_u_66, (copy 14): v_u_73 ]]
        v_u_71 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.GoldnEventUIV2:Clone()
        v_u_71.Name = v_u_1:gen_name(v_u_71.Name)
        p_u_74:set_showing(true)
        p_u_74._native_size = v_u_71.PrimaryPart.Size
        p_u_74._size = p_u_74._native_size
        p_u_74:add_cycle_element(p_u_67, 1, v_u_6:new(v_u_5:new(p_u_74, v_u_71.PrimaryPart, v_u_71.BackButtonSurface), p_u_68, function() --[[ Line: 271 ]]
            --[[ Upvalues: (ref 1): p_u_67, (ref 2): v_u_7, (ref 3): p_u_69, (copy 4): p_u_74 ]]
            p_u_67._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            p_u_69:remove_menu(p_u_74)
        end))
        v_u_72:push_back(v_u_24:new(p_u_67, p_u_68, p_u_69, p_u_74, v_u_71))
        v_u_72:push_back(v_u_51:new(p_u_67, p_u_68, p_u_69, p_u_74, v_u_71))
        v_u_72:push_back(v_u_65:new(p_u_67, p_u_68, p_u_69, p_u_74, v_u_71))
        local function f_create_page_button(p75, p_u_76) --[[ Name: create_page_button ]] --[[ Line: 281 ]]
            --[[ Upvalues: (copy 1): p_u_74, (ref 2): p_u_67, (ref 3): v_u_6, (ref 4): v_u_5, (ref 5): v_u_71, (ref 6): p_u_68, (ref 7): v_u_7, (ref 8): v_u_66 ]]
            local v77 = p_u_74:add_cycle_element(p_u_67, 1, v_u_6:new(v_u_5:new(p_u_74, v_u_71.PrimaryPart, p75), p_u_68, function() --[[ Line: 285 ]]
                --[[ Upvalues: (ref 1): p_u_67, (ref 2): v_u_7, (ref 3): v_u_66, (copy 4): p_u_76, (ref 5): p_u_74 ]]
                p_u_67._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_66 = p_u_76
                p_u_74:update_selected_page()
            end))
            v77:bind_data(v77:get_part().SurfaceGui.Frame.Claimed)
            return v_u_6:button_bind_anim_toggle(v77, function() --[[ Line: 292 ]]
                --[[ Upvalues: (ref 1): p_u_74 ]]
                return p_u_74:get_alpha();
            end);
        end;
        v_u_73:add(1, f_create_page_button(v_u_71.Challenge1Button, 1))
        v_u_73:add(2, f_create_page_button(v_u_71.Challenge2Button, 2))
        v_u_73:add(3, f_create_page_button(v_u_71.Challenge3Button, 3))
        p_u_74:update_selected_page()
        p_u_74:transition_update_visual(0)
        p_u_74:layout()
    end;
    v70.update_selected_page = function(_) --[[ Name: update_selected_page ]] --[[ Line: 304 ]]
        --[[ Upvalues: (copy 1): v_u_72, (ref 2): v_u_66, (copy 3): v_u_73, (copy 4): p_u_67, (ref 5): v_u_10 ]]
        for v78, v79 in v_u_72:key_itr() do
            v79:set_visible(v78 == v_u_66)
            v_u_73:get(v78):set_toggle(v78 == v_u_66)
        end;
        local v80 = p_u_67._player_blob_manager:get_player_blob()
        v_u_73:get(1):get_button():get_bound_data().Visible = v_u_10:get_24kgoldn_playerblob_has_claimed_pet(v80)
        v_u_73:get(2):get_button():get_bound_data().Visible = v_u_10:get_24kgoldn_playerblob_has_claimed_gear(v80)
        v_u_73:get(3):get_button():get_bound_data().Visible = v_u_10:get_24kgoldn_has_badge()
    end;
    v70.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 316 ]]
        --[[ Upvalues: (ref 1): v_u_71, (copy 2): p_u_67 ]]
        v_u_71:Destroy()
        p_u_67._bgm_manager:stop_song_preview()
    end;
    v70.visual_update = function(p81, p82, p83) --[[ Name: visual_update ]] --[[ Line: 321 ]]
        --[[ Upvalues: (copy 1): p_u_67 ]]
        if p_u_67:transition_local_camera_cframe_finished() ~= false then
            p81:visual_update_base(p82, p83)
        end;
    end;
    v70.behaviour_update = function(p84, p85, _) --[[ Name: behaviour_update ]] --[[ Line: 328 ]]
        --[[ Upvalues: (copy 1): p_u_67, (copy 2): v_u_72, (ref 3): v_u_66 ]]
        p84:behaviour_update_base(p85, p_u_67)
        v_u_72:get(v_u_66):behaviour_update(p85)
    end;
    local v_u_86 = 1
    local v_u_87 = 1
    v70.layout = function(p88) --[[ Name: layout ]] --[[ Line: 335 ]]
        --[[ Upvalues: (copy 1): p_u_68, (ref 2): v_u_87, (ref 3): v_u_71, (copy 4): v_u_72 ]]
        p88:opt_rescale_to_max_nxy(p_u_68, 0.8, 0.8, v_u_87)
        local v89, v90 = p88:opt_update_cframe_params(p_u_68, {
            ["PositionNXY"] = Vector2.new(0.5, 0.55),
            ["OffsetXYZ"] = p88:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v89 == true then
            v_u_71:SetPrimaryPartCFrame(v90)
        end;
        for _, v91 in v_u_72:key_itr() do
            v91:layout()
        end;
    end;
    v70.set_alpha = function(_, p92) --[[ Name: set_alpha ]] --[[ Line: 350 ]]
        --[[ Upvalues: (ref 1): v_u_86, (ref 2): v_u_1, (ref 3): v_u_71 ]]
        if v_u_86 ~= p92 then
            v_u_86 = p92
            v_u_1:r_set_alpha(v_u_71, v_u_86)
        end;
    end;
    v70.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 356 ]]
        --[[ Upvalues: (ref 1): v_u_86 ]]
        return v_u_86;
    end;
    v70.set_scale = function(_, p93) --[[ Name: set_scale ]] --[[ Line: 357 ]]
        --[[ Upvalues: (ref 1): v_u_87 ]]
        v_u_87 = p93
    end;
    v70.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 358 ]]
        --[[ Upvalues: (ref 1): v_u_87 ]]
        return v_u_87;
    end;
    v70.get_native_size = function(p94) --[[ Name: get_native_size ]] --[[ Line: 360 ]]
        return p94._native_size;
    end;
    v70.get_size = function(p95) --[[ Name: get_size ]] --[[ Line: 363 ]]
        return p95._size;
    end;
    v70.set_size = function(p96, p97) --[[ Name: set_size ]] --[[ Line: 366 ]]
        --[[ Upvalues: (ref 1): v_u_71 ]]
        p96._size = p97
        v_u_71.PrimaryPart.Size = Vector3.new(p97.X, p97.Y, 0)
    end;
    v70.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 370 ]]
        --[[ Upvalues: (ref 1): v_u_71 ]]
        return v_u_71.PrimaryPart.Position;
    end;
    v70.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 373 ]]
        --[[ Upvalues: (ref 1): v_u_71 ]]
        return v_u_71.PrimaryPart.SurfaceGui;
    end;
    v70.set_showing = function(_, p98) --[[ Name: set_showing ]] --[[ Line: 376 ]]
        --[[ Upvalues: (ref 1): v_u_71, (ref 2): v_u_8 ]]
        if p98 then
            v_u_71.Parent = v_u_8:get_world_ui_folder()
        else
            v_u_71.Parent = nil
        end;
    end;
    v70:cons()
    return v70;
end;
return v18;
