-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:44 PM
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
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v_u_11 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_12 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_13 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.PlayerInfo.PurchaseUtils)
local v_u_14 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_15 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_16 = require(game.ReplicatedStorage.Lobby.Util.RobuxShopCategory)
local v17 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_18 = nil
v17:require_client(function() --[[ Line: 29 ]]
    --[[ Upvalues: (ref 1): v_u_18 ]]
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.RobuxShopUI)
end)
return {
    ["new"] = function(_, p_u_19, p_u_20, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_8, (copy 4): v_u_14, (copy 5): v_u_13, (copy 6): v_u_11, (copy 7): v_u_5, (copy 8): v_u_4, (copy 9): v_u_9, (copy 10): v_u_6, (copy 11): v_u_10, (copy 12): v_u_2, (copy 13): v_u_12, (copy 14): v_u_7, (ref 15): v_u_18, (copy 16): v_u_16, (copy 17): v_u_15 ]]
        local v25 = v_u_3:new(p_u_20, p_u_21)
        local v_u_26 = nil
        local v_u_27 = 1
        local v_u_28 = 1
        local v_u_29 = nil
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = 0
        local v_u_39 = 0
        local v_u_40 = 0
        v25.cons = function(p_u_41) --[[ Name: cons ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_1, (ref 3): v_u_8, (copy 4): p_u_19, (ref 5): v_u_40, (ref 6): v_u_14, (copy 7): p_u_22, (ref 8): v_u_13, (ref 9): v_u_11, (ref 10): v_u_38, (ref 11): v_u_5, (ref 12): v_u_4, (copy 13): p_u_20, (ref 14): v_u_9, (copy 15): p_u_23, (copy 16): p_u_21, (ref 17): v_u_6, (ref 18): v_u_30, (ref 19): v_u_31, (ref 20): v_u_36, (ref 21): v_u_37, (ref 22): v_u_29, (ref 23): v_u_10, (ref 24): v_u_2, (ref 25): v_u_12, (ref 26): v_u_35, (ref 27): v_u_34, (ref 28): v_u_33, (ref 29): v_u_32, (ref 30): v_u_7 ]]
            v_u_26 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.UpgradeBoostUI:Clone()
            v_u_26.Name = v_u_1:gen_name(v_u_26.Name)
            v_u_26.Parent = v_u_8:get_world_ui_folder()
            p_u_41._native_size = v_u_26.PrimaryPart.Size
            p_u_41._size = p_u_41._native_size
            local v_u_42 = p_u_19._player_blob_manager:get_player_blob()
            v_u_40 = v_u_14:get_ownedid_upgrade_count(v_u_42, p_u_22)
            if v_u_40 > 5 and v_u_13:get_count_of_material(v_u_42, v_u_11:singleton():get_upgrade_protect_material_id()) > 0 then
                v_u_38 = 1
            end;
            p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.InfoButton), p_u_20, function() --[[ Line: 71 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (ref 3): v_u_14, (copy 4): v_u_42, (ref 5): p_u_22, (ref 6): p_u_23, (ref 7): v_u_11, (ref 8): v_u_40, (ref 9): p_u_21, (ref 10): v_u_6, (ref 11): p_u_20 ]]
                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                local _, v43, v44 = v_u_14:get_pity_count_for_ownedid_upgradeid(v_u_42, p_u_22, p_u_23)
                p_u_21:push_menu(v_u_6:new(p_u_19, p_u_20, p_u_21):set_text("Upgrade Boost", string.format("For upgrading at +%d, every Upgrade Boost will increase Success Rate by +%.2f%% for the current attempt, and increase Success Rate by +%.2f%% for future attempts with the same upgrade.\nCurrent Upgrade: %s\nBoost Count: %d", v_u_40, v_u_11:singleton():get_boost_upgrade_success_lt_d100_roll_for_upgrade_count(v_u_40), v_u_11:singleton():get_pity_boost_upgrade_success_lt_d100_roll_for_upgrade_count(v_u_40), v_u_11:singleton():get_equipment_upgrade_for_id(v43) == nil and "None" or v_u_11:singleton():get_equipment_upgrade_for_id(v43):get_name(), v44)))
            end))
            p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.BackButtonSurface), p_u_20, function() --[[ Line: 102 ]]
                --[[ Upvalues: (copy 1): p_u_41 ]]
                p_u_41:close_menu()
            end))
            local l_Frame_0 = v_u_26.PrimaryPart.SurfaceGui.Frame
            v_u_30 = l_Frame_0.UpgradeBoostDisplay.Notification.Display
            v_u_31 = l_Frame_0.UpgradeProtectDisplay.Notification.Display
            v_u_36 = l_Frame_0.SuccessRateSection.SuccessRateDisplay
            v_u_37 = l_Frame_0.SuccessRateSection.PityBoostRateDisplay
            v_u_29 = v_u_10:new(nil, v_u_26.PrimaryPart.SurfaceGui.Frame.EquipmentDisplay)
            v_u_29:set_owned_obj(v_u_42, p_u_22)
            local l_UpgradeDisplay_0 = v_u_26.PrimaryPart.SurfaceGui.Frame.UpgradeDisplay
            local v45 = v_u_11:singleton():get_equipment_upgrade_for_id(p_u_23)
            l_UpgradeDisplay_0.NameDisplay.Text = v45:get_name()
            l_UpgradeDisplay_0.IconSection.Icon.Image = v45:get_icon()
            local v46 = v_u_2:new()
            v46:push_back_table_list({
                l_UpgradeDisplay_0.StatDisplay1,
                l_UpgradeDisplay_0.StatDisplay2,
                l_UpgradeDisplay_0.StatDisplay3,
                l_UpgradeDisplay_0.StatDisplay4
            })
            local v47 = v_u_12:get_top_stats(v45:get_gear_statmodifierobj())
            for v48 = 1, v46:count() do
                local v49 = v46:get(v48)
                if v47:count() < v48 then
                    v49.Visible = false
                else
                    local l_Stat_0 = v47:get(v48).Stat
                    local l_Value_0 = v47:get(v48).Value
                    v49.Visible = true
                    v49.Text = string.format("%s%d %s", l_Value_0 < 0 and "-" or "+", math.abs(l_Value_0), v_u_12:type_to_name(l_Stat_0))
                    v49.TextColor3 = v_u_12:gear_attrvalue_get_color(l_Value_0)
                    v_u_10:display_stat_icon_for_sub_text(v49, l_Stat_0, 4)
                end;
            end;
            v_u_35 = p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.UpgradeProtectDownArrow), p_u_20, function() --[[ Line: 149 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (copy 3): p_u_41 ]]
                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                p_u_41:add_upgrade_protect(-1)
            end))
            v_u_34 = p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.UpgradeProtectUpArrow), p_u_20, function() --[[ Line: 158 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (copy 3): p_u_41 ]]
                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                p_u_41:add_upgrade_protect(1)
            end))
            v_u_33 = p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.UpgradeBoostDownArrow), p_u_20, function() --[[ Line: 167 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (copy 3): p_u_41 ]]
                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                p_u_41:add_upgrade_boost(-1)
            end))
            v_u_32 = p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.UpgradeBoostUpArrow), p_u_20, function() --[[ Line: 176 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (copy 3): p_u_41 ]]
                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                p_u_41:add_upgrade_boost(1)
            end))
            p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.BuyUpgradeBoostButton), p_u_20, function() --[[ Line: 185 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (copy 3): p_u_41, (ref 4): v_u_7 ]]
                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN_LONG)
                p_u_41:purchase_button_pressed(v_u_7.ProductID_UpgradeBoost_5)
            end))
            p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.BuyUpgradeProtectButton), p_u_20, function() --[[ Line: 194 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (copy 3): p_u_41, (ref 4): v_u_7 ]]
                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN_LONG)
                p_u_41:purchase_button_pressed(v_u_7.ProductID_UpgradeProtect_5)
            end))
            p_u_41:add_cycle_element(p_u_19, 1, v_u_5:new(v_u_4:new(p_u_41, v_u_26.PrimaryPart, v_u_26.AcceptButton), p_u_20, function() --[[ Line: 203 ]]
                --[[ Upvalues: (copy 1): p_u_41 ]]
                p_u_41:accept_button_pressed()
            end))
            p_u_41:update_ui()
        end;
        v25.add_upgrade_protect = function(p50, p51) --[[ Name: add_upgrade_protect ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_1 ]]
            v_u_38 = v_u_1:clamp(v_u_38 + p51, 0, 1)
            p50:update_ui()
        end;
        v25.add_upgrade_boost = function(p52, p53) --[[ Name: add_upgrade_boost ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_1, (ref 3): v_u_11 ]]
            v_u_39 = v_u_1:clamp(v_u_39 + p53, 0, v_u_11:singleton():get_upgrade_boost_max_count())
            p52:update_ui()
        end;
        v25.update_ui = function(_) --[[ Name: update_ui ]] --[[ Line: 221 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_39, (ref 3): v_u_31, (ref 4): v_u_38, (ref 5): v_u_33, (ref 6): v_u_35, (copy 7): p_u_19, (ref 8): v_u_13, (ref 9): v_u_11, (ref 10): v_u_32, (ref 11): v_u_34, (ref 12): v_u_14, (copy 13): p_u_22, (copy 14): p_u_23, (ref 15): v_u_40, (ref 16): v_u_36, (ref 17): v_u_37 ]]
            v_u_30.Text = tostring(v_u_39)
            v_u_31.Text = tostring(v_u_38)
            v_u_33:set_visible(v_u_39 > 0)
            v_u_35:set_visible(v_u_38 > 0)
            local v54 = p_u_19._player_blob_manager:get_player_blob()
            local v55 = v_u_32
            local v56
            if v_u_39 < v_u_13:get_count_of_material(v54, v_u_11:singleton():get_upgrade_boost_material_id()) + v_u_13:get_count_of_material(v54, v_u_11:singleton():get_upgrade_boost_untradeable_material_id()) then
                v56 = v_u_39 < v_u_11:singleton():get_upgrade_boost_max_count()
            else
                v56 = false
            end;
            v55:set_visible(v56)
            local v57 = v_u_34
            local v58
            if v_u_38 < v_u_13:get_count_of_material(v54, v_u_11:singleton():get_upgrade_protect_material_id()) + v_u_13:get_count_of_material(v54, v_u_11:singleton():get_upgrade_protect_untradeable_material_id()) then
                v58 = v_u_38 < 1
            else
                v58 = false
            end;
            v57:set_visible(v58)
            local v59, _, v60 = v_u_14:get_pity_count_for_ownedid_upgradeid(v54, p_u_22, p_u_23)
            local v61, v62 = v_u_11:singleton():get_boost_upgrade_success_lt_d100_roll_for_upgrade_count_and_boost_count(v_u_40, v_u_39, v59)
            v_u_36.Text = string.format("%.2f", v61) .. "%"
            if v62 > 0 then
                v_u_37.Text = string.format("Success rate is increased by %.2f%% from previous Upgrade Boosts.", v62)
                return;
            elseif v60 > 0 then
                v_u_37.Text = "Attempting this upgrade will reset current Upgrade Boost count."
            else
                v_u_37.Text = "Success rate will be increased for every Upgrade Boost used."
            end;
        end;
        v25.purchase_button_pressed = function(_, _) --[[ Name: purchase_button_pressed ]] --[[ Line: 259 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_16, (copy 3): p_u_21, (copy 4): p_u_19, (copy 5): p_u_20 ]]
            v_u_18:set_selected_category(v_u_16.Upgrade)
            p_u_21:push_menu(v_u_18:new(p_u_19, p_u_20, p_u_21))
        end;
        v25.accept_button_pressed = function(p_u_63) --[[ Name: accept_button_pressed ]] --[[ Line: 267 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_9, (copy 3): p_u_21, (ref 4): v_u_6, (copy 5): p_u_20, (copy 6): p_u_23, (copy 7): p_u_22, (ref 8): v_u_38, (ref 9): v_u_39, (ref 10): v_u_14, (ref 11): v_u_11, (ref 12): v_u_15, (ref 13): v_u_40 ]]
            local function f_perform_upgrade_attempt() --[[ Name: perform_upgrade_attempt ]] --[[ Line: 268 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (ref 3): p_u_21, (ref 4): v_u_6, (ref 5): p_u_20, (ref 6): p_u_23, (ref 7): p_u_22, (ref 8): v_u_38, (ref 9): v_u_39, (ref 10): v_u_14, (ref 11): v_u_11, (ref 12): v_u_15, (copy 13): p_u_63 ]]
                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN_LONG)
                local v_u_64 = p_u_21:push_menu(v_u_6:new(p_u_19, p_u_20, p_u_21):set_text("Upgrading...", ""):set_close_button_visible(false))
                p_u_19._shop_local_protocol:try_craft_gear_boost_upgrade(p_u_23, p_u_22, v_u_38, v_u_39, function(p65, p66, p_u_67, p_u_68, p69) --[[ Line: 276 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (copy 2): v_u_64, (ref 3): v_u_6, (ref 4): p_u_19, (ref 5): p_u_20, (ref 6): v_u_14, (ref 7): p_u_22, (ref 8): v_u_11, (ref 9): p_u_23, (ref 10): v_u_15, (ref 11): v_u_9, (ref 12): p_u_63 ]]
                    local v_u_70 = string.format("%.2f", 100 - p69)
                    if p65 == true then
                        p_u_19._player_blob_manager:do_sync(function(p71) --[[ Line: 284 ]]
                            --[[ Upvalues: (ref 1): v_u_14, (ref 2): p_u_22, (ref 3): p_u_21, (ref 4): v_u_64, (ref 5): v_u_11, (ref 6): p_u_23, (ref 7): v_u_15, (copy 8): p_u_67, (ref 9): p_u_19, (ref 10): v_u_9, (copy 11): p_u_68, (copy 12): v_u_70, (ref 13): v_u_6, (ref 14): p_u_20, (ref 15): p_u_63 ]]
                            local v72 = v_u_14:playerblob_ownedid_to_equipmentid(p71, p_u_22)
                            p_u_21:remove_menu(v_u_64)
                            local v73 = v_u_14:get_ownedid_upgrade_count(p71, p_u_22)
                            local v74 = tostring(v_u_11:singleton():get_equipment_upgrade_for_id(p_u_23):get_name())
                            local v75 = tostring(v_u_15:singleton():get_equipment_for_id(v72):get_name())
                            local v76, v77
                            if p_u_67 == true then
                                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_FANFARE)
                                v76 = string.format("Added upgrade \"%s\" to \"%s +%d\".", v74, v75, tonumber(v73) - 1)
                                v77 = "Upgrade success!"
                            else
                                p_u_19._sfx_manager:play_sfx(v_u_9.SFX_FAIL)
                                v77 = "Upgrade failed..."
                                if p_u_68 then
                                    v76 = string.format("Upgrade failed (Roll: %s). \"%s +%d\" protected.", v_u_70, v75, (tonumber(v73)))
                                else
                                    v76 = string.format("Upgrade failed (Roll: %s). Reduced to \"%s +%d\".", v_u_70, v75, (tonumber(v73)))
                                end;
                            end;
                            p_u_21:push_menu(v_u_6:new(p_u_19, p_u_20, p_u_21):set_text(v77, v76))
                            p_u_21:remove_menu(p_u_63)
                        end)
                    else
                        p_u_21:remove_menu(v_u_64)
                        p_u_21:push_menu(v_u_6:new(p_u_19, p_u_20, p_u_21):set_text("Upgrade failed.", p66))
                    end;
                end)
            end;
            if v_u_40 > 5 and v_u_38 == 0 then
                p_u_21:push_menu(v_u_6:new(p_u_19, p_u_20, p_u_21):set_text("Upgrade without protect?", "If an upgrade fails, the upgraded gear will lose all upgrades above +5."):set_okay_button_fn(function() --[[ Line: 321 ]]
                    --[[ Upvalues: (copy 1): f_perform_upgrade_attempt ]]
                    f_perform_upgrade_attempt()
                end))
            else
                f_perform_upgrade_attempt()
            end;
        end;
        v25.layout = function(p78) --[[ Name: layout ]] --[[ Line: 330 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_28, (ref 3): v_u_26 ]]
            p78:opt_rescale_to_max_nxy(p_u_20, 0.8, 0.8, v_u_28)
            local v79, v80 = p78:opt_update_cframe_params(p_u_20, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p78:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v79 == true then
                v_u_26:SetPrimaryPartCFrame(v80)
            end;
        end;
        v25.visual_update = function(p81, p82, p83) --[[ Name: visual_update ]] --[[ Line: 342 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            p81:visual_update_base(p82, p83)
            v_u_29:visual_update(p82)
        end;
        v25.close_menu = function(p84) --[[ Name: close_menu ]] --[[ Line: 347 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_9, (copy 3): p_u_21 ]]
            p_u_19._sfx_manager:play_sfx(v_u_9.SFX_MENU_CLOSE)
            p_u_21:remove_menu(p84)
        end;
        v25.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 352 ]]
            --[[ Upvalues: (ref 1): v_u_26, (copy 2): p_u_24 ]]
            v_u_26:Destroy()
            p_u_24()
        end;
        v25.set_alpha = function(_, p85) --[[ Name: set_alpha ]] --[[ Line: 357 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_1, (ref 3): v_u_26 ]]
            if v_u_27 ~= p85 then
                v_u_27 = p85
                v_u_1:r_set_alpha(v_u_26, v_u_27)
            end;
        end;
        v25.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 363 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        v25.set_scale = function(_, p86) --[[ Name: set_scale ]] --[[ Line: 364 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28 = p86
        end;
        v25.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 365 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v25.get_native_size = function(p87) --[[ Name: get_native_size ]] --[[ Line: 367 ]]
            return p87._native_size;
        end;
        v25.get_size = function(p88) --[[ Name: get_size ]] --[[ Line: 370 ]]
            return p88._size;
        end;
        v25.set_size = function(p89, p90) --[[ Name: set_size ]] --[[ Line: 373 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            p89._size = p90
            v_u_26.PrimaryPart.Size = Vector3.new(p90.X, p90.Y, 0)
        end;
        v25.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 377 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            return v_u_26.PrimaryPart.Position;
        end;
        v25.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 380 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            return v_u_26.PrimaryPart.SurfaceGui;
        end;
        v25:cons()
        return v25;
    end
};
