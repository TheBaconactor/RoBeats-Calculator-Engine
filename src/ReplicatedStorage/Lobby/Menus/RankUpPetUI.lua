-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:43 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_11 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v_u_12 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.MaterialSelectUI)
require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_14 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_15 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_16 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_17 = require(game.ReplicatedStorage.Pets.PetUtils)
return {
    ["new"] = function(_, p_u_18, p_u_19, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_2, (copy 4): v_u_10, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_7, (copy 8): v_u_11, (copy 9): v_u_12, (copy 10): v_u_17, (copy 11): v_u_13, (copy 12): v_u_15, (copy 13): v_u_6, (copy 14): v_u_14, (copy 15): v_u_8, (copy 16): v_u_16, (copy 17): v_u_9 ]]
        local v22 = v_u_3:new(p_u_19, p_u_20)
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local function f_set_bar_num_div(p29, p30) --[[ Name: set_bar_num_div ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_27, (ref 3): v_u_28 ]]
            local v31 = Vector2.new(437, 24)
            local v32 = Vector2.new(740, 46)
            local v33 = v_u_1:clamp(p29 / p30, 0, 1)
            v_u_27.Text = string.format("%s / %s Points Required", v_u_1:comma_value(p29), v_u_1:comma_value(p30))
            v_u_28.ImageRectSize = v31 * Vector2.new(v33, 1)
            v_u_28.Size = UDim2.new(0, v32.X * v33, 0, v32.Y)
        end;
        local v_u_34 = v_u_2:new()
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_46 = v_u_10:new():set_fn_get_data_list(function() --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): v_u_34 ]]
            return v_u_34:key_list();
        end):set_fn_set_element_data(function(p39, p40) --[[ Line: 50 ]]
            if p40 == nil then
                p39:set_visible(false)
            else
                p39:set_visible(true)
                p39:set_display_element(p40)
            end;
        end):set_fn_next_prev_visible(function(p41, p42) --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_38 ]]
            v_u_37:set_visible(p41)
            v_u_38:set_visible(p42)
        end):set_fn_update_page_display(function(p43, p44) --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            if p44 <= 1 then
                v_u_35.Text = string.format("Materials Used")
            else
                v_u_35.Text = string.format("Materials Used (%d/%d)", p43, p44)
            end;
        end):set_fn_is_empty(function(p45) --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            v_u_36.Visible = p45
        end)
        v22.cons = function(p_u_47) --[[ Name: cons ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_1, (ref 3): v_u_24, (ref 4): v_u_28, (ref 5): v_u_27, (ref 6): v_u_35, (ref 7): v_u_36, (ref 8): v_u_38, (copy 9): p_u_18, (ref 10): v_u_5, (ref 11): v_u_4, (copy 12): p_u_19, (ref 13): v_u_7, (copy 14): v_u_46, (ref 15): v_u_37, (ref 16): v_u_11, (ref 17): v_u_10, (ref 18): v_u_12, (ref 19): v_u_2, (copy 20): v_u_34, (ref 21): v_u_25, (ref 22): v_u_17, (copy 23): p_u_21, (copy 24): p_u_20, (ref 25): v_u_13, (ref 26): v_u_15, (ref 27): v_u_6, (ref 28): v_u_26, (ref 29): v_u_14, (ref 30): v_u_8 ]]
            v_u_23 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Pets.RankUpPetUI:Clone()
            v_u_23.Name = v_u_1:gen_name(v_u_23.Name)
            p_u_47:set_showing(true)
            p_u_47._native_size = v_u_23.PrimaryPart.Size
            p_u_47._size = p_u_47._native_size
            v_u_24 = v_u_23.MainSurface.SurfaceGui.Frame
            v_u_28 = v_u_24.BarSection.BarFillYellow
            v_u_27 = v_u_24.BarSection.ExpDisplay
            v_u_35 = v_u_24.MaterialsUsedTitleDisplay
            v_u_36 = v_u_24.SelectedItemSection.EmptyDisplay
            v_u_38 = p_u_47:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(p_u_47, v_u_23.PrimaryPart, v_u_23.ArrowLeft), p_u_19, function() --[[ Line: 91 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (ref 3): v_u_46 ]]
                p_u_18._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_46:prev_page()
            end))
            v_u_37 = p_u_47:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(p_u_47, v_u_23.PrimaryPart, v_u_23.ArrowRight), p_u_19, function() --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (ref 3): v_u_46 ]]
                p_u_18._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_46:next_page()
            end))
            local function v51(p48) --[[ Line: 106 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_10, (copy 3): p_u_47, (ref 4): v_u_23, (ref 5): v_u_12, (ref 6): v_u_2, (ref 7): v_u_34 ]]
                local l_Frame_0 = p48.PrimaryPart.SurfaceGui.Frame
                local l_Icon_0 = l_Frame_0.Icon
                local v_u_49 = v_u_11:create_display_wrapper(l_Frame_0.Notification, l_Frame_0.Notification.Display)
                return v_u_10.DisplayElement:new(p_u_47, v_u_23.PrimaryPart, p48):set_fn_set_display_element(function(p50) --[[ Line: 113 ]]
                    --[[ Upvalues: (copy 1): l_Icon_0, (ref 2): v_u_12, (copy 3): v_u_49, (ref 4): v_u_2, (ref 5): v_u_34 ]]
                    l_Icon_0.Image = v_u_12:singleton():get_material_icon(p50)
                    v_u_49:update_state(true, v_u_2:counter_get(v_u_34, p50))
                end);
            end;
            local l_MaterialUsedListAnchors_0 = v_u_23.MaterialUsedListAnchors
            v_u_46:create_list_elements_from_anchors_and_proto({
                l_MaterialUsedListAnchors_0.Anchor1,
                l_MaterialUsedListAnchors_0.Anchor2,
                l_MaterialUsedListAnchors_0.Anchor3,
                l_MaterialUsedListAnchors_0.Anchor4
            }, v_u_23.MaterialUsedItemProto, v_u_23, v51)
            v_u_25 = p_u_47:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(p_u_47, v_u_23.PrimaryPart, v_u_23.AddMaterialsButton), p_u_19, function() --[[ Line: 136 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (ref 3): v_u_17, (ref 4): p_u_21, (ref 5): p_u_20, (ref 6): v_u_13, (ref 7): p_u_19, (ref 8): v_u_15, (ref 9): v_u_2, (ref 10): v_u_34, (ref 11): v_u_6 ]]
                p_u_18._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                local v_u_52 = p_u_18._player_blob_manager:get_player_blob()
                local v_u_53 = v_u_17:playerblob_get_pet_ownedid_ownedpet(v_u_52, p_u_21)
                p_u_20:push_menu(v_u_13:new(p_u_18, p_u_19, p_u_20, function(p54, p55) --[[ Line: 141 ]]
                    --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_52, (ref 3): v_u_2, (ref 4): v_u_34, (ref 5): v_u_6 ]]
                    local v56 = v_u_15:get_count_of_material(v_u_52, p54)
                    local v57 = v_u_2:counter_get(v_u_34, p54)
                    if v57 + p55 <= v56 then
                        v_u_2:counter_increment(v_u_34, p54, p55)
                    else
                        v_u_6:warnf("RankUpPetUI owned_count(%d) current_used_count(%d) selected_material_count(%d)", v56, v57, p55)
                    end;
                end):set_fn_material_ids_filter(function(p58) --[[ Line: 151 ]]
                    --[[ Upvalues: (ref 1): v_u_17, (copy 2): v_u_53 ]]
                    return v_u_17:ownedpet_get_material_id_rank_up_point_amount(v_u_53, p58) <= 0;
                end):set_fn_update_owned_materials_dict(function(p59) --[[ Line: 154 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_34 ]]
                    for v60, v61 in p59:key_itr() do
                        p59:add(v60, v61 - v_u_2:counter_get(v_u_34, v60))
                    end;
                    p59:remove_if(function(p62) --[[ Line: 158 ]]
                        return p62 <= 0;
                    end)
                end))
            end))
            v_u_5:button_add_enabled_anim(v_u_25, function() --[[ Line: 165 ]]
                --[[ Upvalues: (copy 1): p_u_47 ]]
                return p_u_47:get_alpha();
            end)
            v_u_26 = p_u_47:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(p_u_47, v_u_23.PrimaryPart, v_u_23.AcceptButton), p_u_19, function() --[[ Line: 170 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (ref 3): p_u_20, (ref 4): v_u_14, (ref 5): p_u_19, (ref 6): v_u_8, (ref 7): p_u_21, (ref 8): v_u_34, (copy 9): p_u_47 ]]
                p_u_18._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                local v_u_63 = p_u_20:push_menu(v_u_14:new(p_u_18, p_u_19, p_u_20):set_text("Loading...", ""):set_close_button_visible(false))
                p_u_18._evt:wait_on_event_once(v_u_8.EVT_Pet_RankUpServerResponse, function(p64, p65) --[[ Line: 173 ]]
                    --[[ Upvalues: (ref 1): p_u_20, (copy 2): v_u_63, (ref 3): v_u_14, (ref 4): p_u_18, (ref 5): p_u_19, (ref 6): v_u_7 ]]
                    if p64 == true then
                        p_u_18._player_blob_manager:do_sync(function() --[[ Line: 179 ]]
                            --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_63, (ref 3): p_u_18, (ref 4): v_u_7 ]]
                            p_u_20:remove_menu(v_u_63)
                            p_u_18._sfx_manager:play_sfx(v_u_7.SFX_ACQUIRE)
                        end)
                    else
                        p_u_20:remove_menu(v_u_63)
                        p_u_20:push_menu(v_u_14:new(p_u_18, p_u_19, p_u_20):set_text("Failed", p65))
                    end;
                end)
                p_u_18._evt:fire_event_to_server(v_u_8.EVT_Pet_RankUpClientRequest, p_u_21, v_u_34:get_table())
                p_u_20:remove_menu(p_u_47)
            end))
            v_u_5:button_add_enabled_anim(v_u_26, function() --[[ Line: 189 ]]
                --[[ Upvalues: (copy 1): p_u_47 ]]
                return p_u_47:get_alpha();
            end)
            p_u_47:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(p_u_47, v_u_23.PrimaryPart, v_u_23.BackButtonSurface), p_u_19, function() --[[ Line: 194 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (ref 3): p_u_20, (copy 4): p_u_47 ]]
                p_u_18._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
                p_u_20:remove_menu(p_u_47)
            end))
            p_u_47:update_display_from_playerblob()
            p_u_47:transition_update_visual(0)
            p_u_47:layout()
        end;
        v22.update_display_from_playerblob = function(_) --[[ Name: update_display_from_playerblob ]] --[[ Line: 206 ]]
            --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_17, (copy 3): p_u_21, (ref 4): v_u_16, (ref 5): v_u_24, (copy 6): v_u_46, (copy 7): v_u_34, (ref 8): v_u_25, (ref 9): v_u_26, (copy 10): f_set_bar_num_div ]]
            local v66 = v_u_17:playerblob_get_pet_ownedid_ownedpet(p_u_18._player_blob_manager:get_player_blob(), p_u_21)
            if v66 == nil then
                return false;
            end;
            if v_u_17:ownedpet_can_rank_up(v66) ~= true then
                return false;
            end;
            local v67 = v_u_16:singleton():get_data_for_petid((v_u_17:ownedpet_get_petid(v66)))
            v_u_24.IconSection.Icon.Image = v67:get_icon()
            v_u_24.RaritySection.Icon.Image = v_u_17:pet_rarity_to_icon(v67:get_rarity())
            v_u_46:page_update()
            local v68 = v_u_17:ownedpet_get_rank_up_point_total_requirement(v66)
            local v69 = v_u_17:ownedpet_get_materialid_to_count_dict_rank_up_point_total(v66, v_u_34)
            v_u_25:set_enabled(v69 < v68)
            v_u_26:set_enabled(v68 <= v69)
            f_set_bar_num_div(v69, v68)
        end;
        v22.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 228 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23:Destroy()
        end;
        local v_u_70 = 1
        local v_u_71 = 1
        v22.layout = function(p72) --[[ Name: layout ]] --[[ Line: 234 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_71, (ref 3): v_u_23, (copy 4): v_u_46 ]]
            p72:opt_rescale_to_max_nxy(p_u_19, 0.8, 0.8, v_u_71)
            local v73, v74 = p72:opt_update_cframe_params(p_u_19, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p72:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v73 == true then
                v_u_23:SetPrimaryPartCFrame(v74)
            end;
            v_u_46:layout()
        end;
        v22.on_refocus = function(p75) --[[ Name: on_refocus ]] --[[ Line: 247 ]]
            p75:update_display_from_playerblob()
        end;
        v22.set_alpha = function(_, p76) --[[ Name: set_alpha ]] --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_70, (ref 2): v_u_1, (ref 3): v_u_23 ]]
            if v_u_70 ~= p76 then
                v_u_70 = p76
                v_u_1:r_set_alpha(v_u_23, v_u_70)
            end;
        end;
        v22.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 257 ]]
            --[[ Upvalues: (ref 1): v_u_70 ]]
            return v_u_70;
        end;
        v22.set_scale = function(_, p77) --[[ Name: set_scale ]] --[[ Line: 258 ]]
            --[[ Upvalues: (ref 1): v_u_71 ]]
            v_u_71 = p77
        end;
        v22.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 259 ]]
            --[[ Upvalues: (ref 1): v_u_71 ]]
            return v_u_71;
        end;
        v22.get_native_size = function(p78) --[[ Name: get_native_size ]] --[[ Line: 261 ]]
            return p78._native_size;
        end;
        v22.get_size = function(p79) --[[ Name: get_size ]] --[[ Line: 264 ]]
            return p79._size;
        end;
        v22.set_size = function(p80, p81) --[[ Name: set_size ]] --[[ Line: 267 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            p80._size = p81
            v_u_23.PrimaryPart.Size = Vector3.new(p81.X, p81.Y, 0)
        end;
        v22.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 271 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23.PrimaryPart.Position;
        end;
        v22.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 274 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23.PrimaryPart.SurfaceGui;
        end;
        v22.set_showing = function(_, p82) --[[ Name: set_showing ]] --[[ Line: 277 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_9 ]]
            if p82 then
                v_u_23.Parent = v_u_9:get_world_ui_folder()
            else
                v_u_23.Parent = nil
            end;
        end;
        v22:cons()
        return v22;
    end
};
