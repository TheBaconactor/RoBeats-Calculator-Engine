-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:46 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v_u_10 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_11 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_12 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.PlayerInfo.PurchaseUtils)
local v_u_13 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_14 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_15 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
return {
    ["new"] = function(_, p_u_16, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_7, (copy 4): v_u_9, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_8, (copy 8): v_u_14, (copy 9): v_u_13, (copy 10): v_u_2, (copy 11): v_u_12, (copy 12): v_u_10, (copy 13): v_u_11, (copy 14): v_u_6, (copy 15): v_u_15 ]]
        local v20 = v_u_3:new(p_u_17, p_u_18)
        local v_u_21 = nil
        local v_u_22 = 1
        local v_u_23 = 1
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local v_u_29 = nil
        v20.cons = function(p_u_30) --[[ Name: cons ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_27, (ref 5): v_u_29, (ref 6): v_u_24, (ref 7): v_u_9, (ref 8): v_u_28, (copy 9): p_u_16, (ref 10): v_u_5, (ref 11): v_u_4, (copy 12): p_u_17, (ref 13): v_u_8, (copy 14): p_u_18, (ref 15): v_u_25, (ref 16): v_u_26, (ref 17): v_u_14, (ref 18): v_u_13, (copy 19): p_u_19, (ref 20): v_u_2 ]]
            v_u_21 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.UpgradeEditUI:Clone()
            v_u_21.Name = v_u_1:gen_name(v_u_21.Name)
            v_u_21.Parent = v_u_7:get_world_ui_folder()
            p_u_30._native_size = v_u_21.PrimaryPart.Size
            p_u_30._size = p_u_30._native_size
            v_u_27 = v_u_21.PrimaryPart.SurfaceGui.Frame
            v_u_29 = v_u_27.EmptyUpgradesDisplay
            v_u_29.Visible = false
            v_u_24 = v_u_9:new(nil, v_u_27.EquipmentDisplay)
            v_u_28 = p_u_30:add_cycle_element(p_u_16, 1, v_u_5:new(v_u_4:new(p_u_30, v_u_21.PrimaryPart, v_u_21.RemoveUpgradeButton), p_u_17, function() --[[ Line: 58 ]]
                --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (copy 3): p_u_30 ]]
                p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                p_u_30:on_remove_upgrade_button_pressed()
            end))
            v_u_5:button_add_enabled_anim(v_u_28, function() --[[ Line: 63 ]]
                --[[ Upvalues: (copy 1): p_u_30 ]]
                return p_u_30:get_alpha();
            end)
            p_u_30:add_cycle_element(p_u_16, 1, v_u_5:new(v_u_4:new(p_u_30, v_u_21.PrimaryPart, v_u_21.BackButtonSurface), p_u_17, function() --[[ Line: 68 ]]
                --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (ref 3): p_u_18, (copy 4): p_u_30 ]]
                p_u_16._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
                p_u_18:remove_menu(p_u_30)
            end))
            v_u_25 = v_u_27.UpgradeNumberDisplay
            local v_u_31 = p_u_30:add_cycle_element(p_u_16, 1, v_u_5:new(v_u_4:new(p_u_30, v_u_21.PrimaryPart, v_u_21.ArrowLeft), p_u_17, function() --[[ Line: 79 ]]
                --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (ref 3): v_u_26 ]]
                p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                v_u_26:prev_page()
            end))
            local v_u_32 = p_u_30:add_cycle_element(p_u_16, 1, v_u_5:new(v_u_4:new(p_u_30, v_u_21.PrimaryPart, v_u_21.ArrowRight), p_u_17, function() --[[ Line: 88 ]]
                --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (ref 3): v_u_26 ]]
                p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                v_u_26:next_page()
            end))
            v_u_26 = v_u_14:new():set_fn_get_data_list(function() --[[ Line: 95 ]]
                --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_13, (ref 3): p_u_19, (ref 4): v_u_2 ]]
                local _, v33 = v_u_13:playerblob_ownedid_to_equipmentid(p_u_16._player_blob_manager:get_player_blob(), p_u_19)
                return v_u_2:new():push_back_table_list(v33.Upgrades);
            end):set_fn_set_element_data(function(p34, p35) --[[ Line: 100 ]]
                --[[ Upvalues: (copy 1): p_u_30 ]]
                p_u_30:display_selected_upgrade(p34.UpgradeDisplayFrame, p34.UpgradeStatDisplays, p35)
            end):set_fn_next_prev_visible(function(p36, p37) --[[ Line: 103 ]]
                --[[ Upvalues: (copy 1): v_u_32, (copy 2): v_u_31 ]]
                v_u_32:set_visible(p36)
                v_u_31:set_visible(p37)
            end):set_fn_update_page_display(function(p38, p39) --[[ Line: 107 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                v_u_25.Text = string.format("Upgrade %d (of %d)", p38, p39)
            end):set_fn_is_empty(function(p40) --[[ Line: 110 ]]
                --[[ Upvalues: (ref 1): v_u_29 ]]
                v_u_29.Visible = p40
            end):set_do_wrap(true)
            local l_UpgradeDisplay_0 = v_u_27.UpgradeDisplay
            v_u_26:push_display_element({
                ["UpgradeDisplayFrame"] = l_UpgradeDisplay_0,
                ["UpgradeStatDisplays"] = v_u_2:new():push_back_table_list({
                    l_UpgradeDisplay_0.StatDisplay1,
                    l_UpgradeDisplay_0.StatDisplay2,
                    l_UpgradeDisplay_0.StatDisplay3,
                    l_UpgradeDisplay_0.StatDisplay4
                })
            })
            v_u_26:page_update()
            p_u_30:update_remove_upgrade_section_display()
        end;
        v20.update_remove_upgrade_section_display = function(_) --[[ Name: update_remove_upgrade_section_display ]] --[[ Line: 131 ]]
            --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_24, (copy 3): p_u_19, (ref 4): v_u_12, (ref 5): v_u_10, (ref 6): v_u_27, (ref 7): v_u_26, (ref 8): v_u_28 ]]
            local v41 = p_u_16._player_blob_manager:get_player_blob()
            v_u_24:set_owned_obj(v41, p_u_19)
            local v42 = v_u_12:get_count_of_material(v41, v_u_10:singleton():get_upgrade_cleaner_material_id())
            v_u_27.UpgradeCleanerCountDisplay.Text = string.format("Upgrade Cleaners: %d", v42)
            if v42 > 0 and (v_u_26 and v_u_26:get_data_list():get(v_u_26:get_i_offset() + 1) ~= nil) then
                v_u_28:set_enabled(true)
            else
                v_u_28:set_enabled(false)
            end;
        end;
        v20.display_selected_upgrade = function(_, p43, p44, p45) --[[ Name: display_selected_upgrade ]] --[[ Line: 144 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_9 ]]
            if p45 == nil then
                p43.Visible = false
                v_u_28:set_enabled(false)
            else
                p43.Visible = true
                local v46 = v_u_10:singleton():get_equipment_upgrade_for_id(p45.UpgradeID)
                p43.NameDisplay.Text = v46:get_name()
                p43.IconSection.Icon.Image = v46:get_icon()
                local v47 = v_u_11:get_top_stats(v46:get_gear_statmodifierobj())
                for v48 = 1, p44:count() do
                    local v49 = p44:get(v48)
                    if v47:count() < v48 then
                        v49.Visible = false
                    else
                        local l_Stat_0 = v47:get(v48).Stat
                        local l_Value_0 = v47:get(v48).Value
                        v49.Visible = true
                        v49.Text = string.format("%s%d %s", l_Value_0 < 0 and "-" or "+", math.abs(l_Value_0), v_u_11:type_to_name(l_Stat_0))
                        v49.TextColor3 = v_u_11:gear_attrvalue_get_color(l_Value_0)
                        v_u_9:display_stat_icon_for_sub_text(v49, l_Stat_0, 4)
                    end;
                end;
            end;
        end;
        v20.on_remove_upgrade_button_pressed = function(_) --[[ Name: on_remove_upgrade_button_pressed ]] --[[ Line: 177 ]]
            --[[ Upvalues: (ref 1): v_u_26, (copy 2): p_u_18, (ref 3): v_u_6, (copy 4): p_u_16, (copy 5): p_u_17, (ref 6): v_u_10, (ref 7): v_u_15, (copy 8): p_u_19 ]]
            local v50 = v_u_26:get_data_list():get(v_u_26:get_i_offset() + 1)
            local l_Index_0 = v50.Index
            p_u_18:push_menu(v_u_6:new(p_u_16, p_u_17, p_u_18):set_text("Confirm", string.format("Are you sure you want to remove \'%s\'?", v_u_10:singleton():get_equipment_upgrade_for_id(v50.UpgradeID):get_name())):set_okay_button_fn(function() --[[ Line: 186 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_6, (ref 3): p_u_16, (ref 4): p_u_17, (ref 5): v_u_15, (ref 6): p_u_19, (copy 7): l_Index_0 ]]
                local v_u_51 = p_u_18:push_menu(v_u_6:new(p_u_16, p_u_17, p_u_18):set_text("Cleaning...", ""):set_close_button_visible(false))
                p_u_16._evt:wait_on_event_once(v_u_15.EVT_Crafting_RemoveUpgradeServerResponse, function(p52, p53) --[[ Line: 188 ]]
                    --[[ Upvalues: (ref 1): p_u_18, (copy 2): v_u_51, (ref 3): v_u_6, (ref 4): p_u_16, (ref 5): p_u_17 ]]
                    if p52 == true then
                        p_u_16._player_blob_manager:do_sync(function(_) --[[ Line: 194 ]]
                            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_51 ]]
                            p_u_18:remove_menu(v_u_51)
                        end)
                    else
                        p_u_18:remove_menu(v_u_51)
                        p_u_18:push_menu(v_u_6:new(p_u_16, p_u_17, p_u_18):set_text("Failed", p53))
                    end;
                end)
                p_u_16._evt:fire_event_to_server(v_u_15.EVT_Crafting_RemoveUpgradeClientRequest, p_u_19, l_Index_0)
            end))
        end;
        v20.layout = function(p54) --[[ Name: layout ]] --[[ Line: 203 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_23, (ref 3): v_u_21 ]]
            p54:opt_rescale_to_max_nxy(p_u_17, 0.8, 0.8, v_u_23)
            local v55, v56 = p54:opt_update_cframe_params(p_u_17, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p54:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v55 == true then
                v_u_21:SetPrimaryPartCFrame(v56)
            end;
        end;
        v20.visual_update = function(p57, p58, p59) --[[ Name: visual_update ]] --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            p57:visual_update_base(p58, p59)
            v_u_24:visual_update(p58)
        end;
        v20.on_refocus = function(p60) --[[ Name: on_refocus ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26:set_i_offset(0)
            v_u_26:page_update()
            p60:update_remove_upgrade_section_display()
        end;
        v20.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21:Destroy()
        end;
        v20.set_alpha = function(_, p61) --[[ Name: set_alpha ]] --[[ Line: 230 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_1, (ref 3): v_u_21 ]]
            if v_u_22 ~= p61 then
                v_u_22 = p61
                v_u_1:r_set_alpha(v_u_21, v_u_22)
            end;
        end;
        v20.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 236 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        v20.set_scale = function(_, p62) --[[ Name: set_scale ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = p62
        end;
        v20.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 238 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        v20.get_native_size = function(p63) --[[ Name: get_native_size ]] --[[ Line: 240 ]]
            return p63._native_size;
        end;
        v20.get_size = function(p64) --[[ Name: get_size ]] --[[ Line: 243 ]]
            return p64._size;
        end;
        v20.set_size = function(p65, p66) --[[ Name: set_size ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            p65._size = p66
            v_u_21.PrimaryPart.Size = Vector3.new(p66.X, p66.Y, 0)
        end;
        v20.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 250 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21.PrimaryPart.Position;
        end;
        v20.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 253 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21.PrimaryPart.SurfaceGui;
        end;
        v20.set_showing = function(_, p67) --[[ Name: set_showing ]] --[[ Line: 256 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_7 ]]
            if p67 then
                v_u_21.Parent = v_u_7:get_world_ui_folder()
            else
                v_u_21.Parent = nil
            end;
        end;
        v20:cons()
        return v20;
    end
};
