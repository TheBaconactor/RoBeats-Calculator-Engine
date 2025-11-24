-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.SPUIButton)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIDisplay)
local v_u_5 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.DanceSelectUI)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
return {
    ["new"] = function(_, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 17 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_2, (copy 5): v_u_6, (copy 6): v_u_8, (copy 7): v_u_7, (copy 8): v_u_10, (copy 9): v_u_5, (copy 10): v_u_9 ]]
        local v17 = {
            ["playerblob_updated"] = function(p16) --[[ Name: playerblob_updated ]] --[[ Line: 184 ]]
                p16:update_dance_button_state()
            end
        }
        local v_u_18 = nil
        local v_u_19 = v_u_1:new()
        local v_u_20 = false
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        v17.cons = function(p_u_25) --[[ Name: cons ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_18, (ref 3): v_u_4, (copy 4): p_u_12, (ref 5): v_u_24, (copy 6): p_u_14, (copy 7): p_u_11, (ref 8): v_u_3, (ref 9): v_u_2, (ref 10): v_u_6, (ref 11): v_u_20, (ref 12): v_u_21, (ref 13): v_u_22, (ref 14): v_u_23, (copy 15): p_u_13, (ref 16): v_u_8, (ref 17): v_u_7, (ref 18): v_u_10, (ref 19): v_u_5, (copy 20): v_u_19 ]]
            local l_DanceButtonDrawer_0 = p_u_15.DanceButtonDrawer
            v_u_18 = v_u_4:new(l_DanceButtonDrawer_0, p_u_12, true):set_position_nxy(0, 0.5):set_anchor_rnxy(0, 0.5)
            v_u_24 = l_DanceButtonDrawer_0.OpenSurface.SurfaceGui
            p_u_14:add_cycle_element(p_u_11, 1, v_u_3:new(v_u_2:new(v_u_18, v_u_18:get_part(), l_DanceButtonDrawer_0.MenuButton), p_u_12, function() --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_6, (ref 3): v_u_20, (copy 4): p_u_25 ]]
                p_u_11._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                v_u_20 = not v_u_20
                p_u_25:update_open_state()
            end))
            v_u_21 = p_u_14:add_cycle_element(p_u_11, 1, v_u_3:new(v_u_2:new(v_u_18, v_u_18:get_part(), l_DanceButtonDrawer_0.TopArrowSurface), p_u_12, function() --[[ Line: 48 ]]
                --[[ Upvalues: (copy 1): p_u_25, (ref 2): p_u_11, (ref 3): v_u_6 ]]
                p_u_25:move_page_by(-1)
                p_u_11._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            end))
            v_u_22 = p_u_14:add_cycle_element(p_u_11, 1, v_u_3:new(v_u_2:new(v_u_18, v_u_18:get_part(), l_DanceButtonDrawer_0.BottomArrowSurface), p_u_12, function() --[[ Line: 57 ]]
                --[[ Upvalues: (copy 1): p_u_25, (ref 2): p_u_11, (ref 3): v_u_6 ]]
                p_u_25:move_page_by(1)
                p_u_11._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            end))
            v_u_23 = p_u_14:add_cycle_element(p_u_11, 1, v_u_3:new(v_u_2:new(v_u_18, v_u_18:get_part(), l_DanceButtonDrawer_0.DanceSelectButton), p_u_12, function() --[[ Line: 68 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_6, (ref 3): p_u_13, (ref 4): v_u_8, (ref 5): p_u_12 ]]
                p_u_11._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                p_u_13:push_menu(v_u_8:new(p_u_11, p_u_12, p_u_13))
            end))
            local l_DanceButtonProto_0 = l_DanceButtonDrawer_0.DanceButtonProto
            l_DanceButtonProto_0.Parent = nil
            for v26 = 1, 6 do
                local l_Anchors_0 = l_DanceButtonDrawer_0.Anchors["Anchor" .. tostring(v26)]
                local v27 = l_DanceButtonProto_0:Clone()
                v27.Parent = l_DanceButtonDrawer_0
                v27.Position = l_Anchors_0.Position
                local v_u_28 = nil
                v_u_28 = v_u_3:new(v_u_2:new(v_u_18, v_u_18:get_part(), v27), p_u_12, function() --[[ Line: 89 ]]
                    --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_6, (ref 3): v_u_28, (ref 4): v_u_7, (ref 5): v_u_10, (ref 6): v_u_5 ]]
                    p_u_11._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    local v_u_29 = v_u_28:get_bound_data()
                    if v_u_7:singleton():contains_dance_for_id(v_u_29) then
                        if v_u_10:is_dance_equipped(p_u_11._player_blob_manager:get_player_blob(), v_u_29) then
                            spawn(function() --[[ Line: 95 ]]
                                --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_29, (ref 3): p_u_11 ]]
                                local v30 = v_u_7:singleton():get_dance_animation_for_id(v_u_29)
                                p_u_11._animate_script:play_animation_instance(v30)
                                p_u_11._follow_npc_manager:on_local_character_play_animation(v30)
                            end)
                            return;
                        end;
                    else
                        v_u_5:errf("DanceHUD invalid dance_id(%s)", (tostring(v_u_29)))
                    end;
                end)
                v_u_19:push_back(p_u_14:add_cycle_element(p_u_11, 1, v_u_28))
            end;
            p_u_25:update_dance_button_state()
            p_u_25:update_open_state()
        end;
        local function f_get_dances_ids_list() --[[ Name: get_dances_ids_list ]] --[[ Line: 112 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_10, (ref 3): v_u_1, (ref 4): v_u_7 ]]
            local v31 = v_u_10:get_owned_danceid_to_equipped_dict((p_u_11._player_blob_manager:get_player_blob()))
            local v32 = v_u_1:new()
            for v33, _ in v_u_7:singleton():key_itr() do
                if v31:contains(v33) and v31:get(v33) == true then
                    v32:push_back(v33)
                end;
            end;
            return v32;
        end;
        local v_u_34 = 0
        v17.update_dance_button_state = function(_) --[[ Name: update_dance_button_state ]] --[[ Line: 125 ]]
            --[[ Upvalues: (copy 1): f_get_dances_ids_list, (ref 2): v_u_34, (copy 3): v_u_19, (ref 4): v_u_20, (ref 5): v_u_9, (ref 6): v_u_7, (ref 7): v_u_22, (ref 8): v_u_21, (ref 9): v_u_23 ]]
            local v35 = f_get_dances_ids_list()
            local v36 = v_u_34 * v_u_19:count()
            for v37 = 1, v_u_19:count() do
                local v38 = v_u_19:get(v37)
                local v39 = v36 + v37
                if v_u_20 == true then
                    if v39 <= v35:count() then
                        v38:set_visible(true)
                        local v40 = v35:get(v39)
                        v38:bind_data(v40)
                        local l_Frame_0 = v38:get_part().SurfaceGui.Frame
                        l_Frame_0.NameDisplay.TextColor3 = v_u_9:rarity_to_color(v_u_7:singleton():get_dance_rarity_for_id(v40))
                        l_Frame_0.Icon.Image = v_u_7:singleton():get_dance_icon_for_id(v40)
                        l_Frame_0.NameDisplay.Text = string.format("[%d] %s", v40, v_u_7:singleton():get_dance_name_for_id(v40))
                    else
                        v38:set_visible(false)
                    end;
                else
                    v38:set_visible(false)
                end;
            end;
            if v_u_20 == true then
                v_u_22:set_visible(true)
                v_u_21:set_visible(true)
                if v_u_23 then
                    v_u_23:set_visible(true)
                    return;
                end;
            else
                v_u_22:set_visible(false)
                v_u_21:set_visible(false)
                if v_u_23 then
                    v_u_23:set_visible(false)
                end;
            end;
        end;
        v17.move_page_by = function(p41, p42) --[[ Name: move_page_by ]] --[[ Line: 161 ]]
            --[[ Upvalues: (copy 1): f_get_dances_ids_list, (copy 2): v_u_19, (ref 3): v_u_34 ]]
            local v43 = math.ceil(f_get_dances_ids_list():count() / v_u_19:count())
            v_u_34 = v_u_34 + p42
            if v_u_34 < 0 then
                v_u_34 = v43 - 1
            end;
            if v_u_34 > v43 - 1 then
                v_u_34 = 0
            end;
            p41:update_dance_button_state()
        end;
        v17.update_open_state = function(p44) --[[ Name: update_open_state ]] --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_18, (copy 3): p_u_12, (ref 4): v_u_24 ]]
            if v_u_20 then
                v_u_18:set_position_nxy(0, 0.5)
            else
                v_u_18:set_position_nxy(-p_u_12:uiobj_get_size_nxy(v_u_18).X, 0.5)
            end;
            p44:update_dance_button_state()
            v_u_24.Enabled = v_u_20
        end;
        v17.layout = function(p45) --[[ Name: layout ]] --[[ Line: 188 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_18 ]]
            if p_u_12:is_layout_updated() then
                p45:update_open_state()
            end;
            p_u_12:uiobj_rescale_to_max_nxy(v_u_18, 0.25, 0.45, 1)
            v_u_18:layout()
        end;
        v17:cons()
        return v17;
    end
};
