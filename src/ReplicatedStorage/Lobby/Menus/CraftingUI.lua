-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:41 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
v11:require_client(function() --[[ Line: 31 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14, (ref 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_17, (ref 7): v_u_18, (ref 8): v_u_19, (ref 9): v_u_20 ]]
    v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.CraftingGatchaUI)
    v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.MarketplaceUI)
    v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.SongInventoryV2UI)
    v_u_15 = require(game.ReplicatedStorage.Lobby.UI.CraftingUIListElement)
    v_u_16 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabMaterials)
    v_u_17 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabSongs)
    v_u_18 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabGearUpgrades)
    v_u_19 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabGear)
    v_u_20 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabCraftMaterials)
end)
return {
    ["new"] = function(_, p_u_21, p_u_22, p_u_23, p_u_24, p_u_25) --[[ Name: new ]] --[[ Line: 45 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (ref 3): v_u_16, (copy 4): v_u_3, (copy 5): v_u_1, (copy 6): v_u_8, (copy 7): v_u_5, (copy 8): v_u_6, (copy 9): v_u_7, (ref 10): v_u_17, (ref 11): v_u_18, (ref 12): v_u_19, (ref 13): v_u_20, (copy 14): v_u_10, (ref 15): v_u_12, (copy 16): v_u_9, (ref 17): v_u_13, (ref 18): v_u_14, (ref 19): v_u_15 ]]
        local v_u_26 = v_u_4:new(p_u_22, p_u_23)
        local v_u_27 = nil
        local v_u_28 = 1
        local v_u_29 = 1
        local v_u_30 = v_u_2:new()
        local v_u_31 = v_u_2:new()
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        v_u_26.get_craft_button = function(_) --[[ Name: get_craft_button ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            return v_u_35;
        end;
        v_u_26.get_use_button = function(_) --[[ Name: get_use_button ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36;
        end;
        local l_Tab_0 = v_u_16.Tab
        if p_u_24 == nil then
            p_u_24 = l_Tab_0
        end;
        v_u_26.get_current_tab_instance = function(_) --[[ Name: get_current_tab_instance ]] --[[ Line: 64 ]]
            --[[ Upvalues: (copy 1): v_u_30, (ref 2): p_u_24 ]]
            return v_u_30:get(p_u_24);
        end;
        local v_u_37 = v_u_3:new()
        v_u_26.get_list_elements = function(_) --[[ Name: get_list_elements ]] --[[ Line: 67 ]]
            --[[ Upvalues: (copy 1): v_u_37 ]]
            return v_u_37;
        end;
        local v_u_38 = nil
        v_u_26.get_search_name = function(_) --[[ Name: get_search_name ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            return v_u_38:get_search_name();
        end;
        v_u_26.get_sort_type = function(_) --[[ Name: get_sort_type ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            return v_u_38:get_sort_type();
        end;
        v_u_26.get_sort_order = function(_) --[[ Name: get_sort_order ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            return v_u_38:get_sort_order();
        end;
        local v_u_39 = nil
        local v_u_40 = nil
        local v_u_41 = nil
        local v_u_42 = nil
        local v_u_43 = nil
        local v_u_44 = nil
        local v_u_45 = nil
        local v_u_46 = nil
        local v_u_47 = nil
        local v_u_48 = nil
        local function f_update_amount_buttons() --[[ Name: update_amount_buttons ]] --[[ Line: 84 ]]
            --[[ Upvalues: (copy 1): v_u_26, (ref 2): v_u_45, (ref 3): v_u_46, (ref 4): v_u_47, (ref 5): v_u_48 ]]
            if v_u_26:get_current_tab_instance() then
                local v49, v50 = v_u_26:get_current_tab_instance():show_craft_amount_buttons()
                v_u_45:set_visible(v49)
                v_u_46:set_visible(v50)
                local v51, v52 = v_u_26:get_current_tab_instance():show_use_amount_buttons()
                v_u_47:set_visible(v51)
                v_u_48:set_visible(v52)
            end;
        end;
        local function _() --[[ Name: tab_press_clear_search ]] --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            v_u_38:reset()
            v_u_38:raise_changed()
        end;
        v_u_26.cons = function(p_u_53) --[[ Name: cons ]] --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_34, (ref 5): v_u_5, (ref 6): v_u_43, (copy 7): p_u_21, (ref 8): v_u_6, (copy 9): p_u_22, (copy 10): p_u_23, (ref 11): v_u_7, (ref 12): v_u_33, (ref 13): v_u_32, (ref 14): v_u_45, (copy 15): f_update_amount_buttons, (ref 16): v_u_46, (ref 17): v_u_47, (ref 18): v_u_48, (copy 19): v_u_31, (ref 20): v_u_16, (ref 21): v_u_17, (ref 22): v_u_18, (ref 23): v_u_19, (ref 24): v_u_20, (ref 25): v_u_35, (ref 26): v_u_36, (copy 27): v_u_30, (ref 28): v_u_38, (ref 29): v_u_10, (ref 30): v_u_39, (ref 31): v_u_12, (ref 32): v_u_9, (ref 33): v_u_13, (ref 34): v_u_40, (ref 35): v_u_41, (ref 36): v_u_44, (ref 37): v_u_42, (ref 38): v_u_14, (copy 39): p_u_25 ]]
            v_u_27 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.CraftingUI:Clone()
            v_u_27.Name = v_u_1:gen_name(v_u_27.Name)
            v_u_27.Parent = v_u_8:get_world_ui_folder()
            p_u_53._native_size = v_u_27.PrimaryPart.Size
            p_u_53._size = p_u_53._native_size
            v_u_34 = v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.InventoryItemHighlight)
            v_u_34:set_sgui(v_u_34:get_child_part().SurfaceGui)
            v_u_43 = v_u_27.MainSurface.SurfaceGui.Frame.EmptyDisplay
            v_u_43.Text = ""
            v_u_43.Visible = false
            p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.BackButtonSurface), p_u_22, function() --[[ Line: 121 ]]
                --[[ Upvalues: (ref 1): p_u_23, (copy 2): p_u_53, (ref 3): p_u_21, (ref 4): v_u_7 ]]
                p_u_23:remove_menu(p_u_53)
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            end))
            v_u_33 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.BottomArrowSurface), p_u_22, function() --[[ Line: 130 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:get_current_tab_instance():page_down()
                p_u_53:update_current_tab()
            end))
            v_u_32 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.TopArrowSurface), p_u_22, function() --[[ Line: 140 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:get_current_tab_instance():page_up()
                p_u_53:update_current_tab()
            end))
            v_u_45 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.CraftAmountLeftButton), p_u_22, function() --[[ Line: 150 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): f_update_amount_buttons ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:get_current_tab_instance():craft_amount_button_pressed(-1)
                f_update_amount_buttons()
            end))
            v_u_46 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.CraftAmountRightButton), p_u_22, function() --[[ Line: 159 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): f_update_amount_buttons ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:get_current_tab_instance():craft_amount_button_pressed(1)
                f_update_amount_buttons()
            end))
            v_u_47 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.UseAmountLeftButton), p_u_22, function() --[[ Line: 168 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): f_update_amount_buttons ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:get_current_tab_instance():craft_amount_button_pressed(-1)
                f_update_amount_buttons()
            end))
            v_u_48 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.UseAmountRightButton), p_u_22, function() --[[ Line: 177 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): f_update_amount_buttons ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:get_current_tab_instance():craft_amount_button_pressed(1)
                f_update_amount_buttons()
            end))
            v_u_31:add(v_u_16.Tab, p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.MaterialsButton), p_u_22, function() --[[ Line: 187 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): v_u_16 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:set_current_tab_and_update(v_u_16.Tab)
            end)))
            v_u_31:add(v_u_17.Tab, p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.SongsButton), p_u_22, function() --[[ Line: 196 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): v_u_17 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:set_current_tab_and_update(v_u_17.Tab)
            end)))
            v_u_31:add(v_u_18.Tab, p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.GearUpgradeButton), p_u_22, function() --[[ Line: 205 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): v_u_18 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:set_current_tab_and_update(v_u_18.Tab)
            end)))
            v_u_31:add(v_u_19.Tab, p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.GearButton), p_u_22, function() --[[ Line: 214 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): v_u_19 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:set_current_tab_and_update(v_u_19.Tab)
            end)))
            v_u_31:add(v_u_20.Tab, p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.CraftMaterialsButton), p_u_22, function() --[[ Line: 223 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): v_u_20 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_53:set_current_tab_and_update(v_u_20.Tab)
            end)))
            v_u_35 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.CraftButton), p_u_22, function() --[[ Line: 232 ]]
                --[[ Upvalues: (copy 1): p_u_53 ]]
                p_u_53:get_current_tab_instance():craft_pressed()
            end))
            v_u_6:button_add_enabled_anim(v_u_35, function() --[[ Line: 236 ]]
                --[[ Upvalues: (copy 1): p_u_53 ]]
                return p_u_53:get_alpha();
            end)
            v_u_36 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.UseButton), p_u_22, function() --[[ Line: 241 ]]
                --[[ Upvalues: (copy 1): p_u_53 ]]
                p_u_53:get_current_tab_instance():craft_pressed()
            end))
            v_u_6:button_add_enabled_anim(v_u_36, function() --[[ Line: 245 ]]
                --[[ Upvalues: (copy 1): p_u_53 ]]
                return p_u_53:get_alpha();
            end)
            p_u_53:setup_list_elements()
            v_u_30:add(v_u_16.Tab, v_u_16:new(p_u_21, p_u_53, v_u_27))
            v_u_30:add(v_u_17.Tab, v_u_17:new(p_u_21, p_u_53, v_u_27))
            v_u_30:add(v_u_18.Tab, v_u_18:new(p_u_21, p_u_53, v_u_27))
            v_u_30:add(v_u_19.Tab, v_u_19:new(p_u_21, p_u_53, v_u_27))
            v_u_30:add(v_u_20.Tab, v_u_20:new(p_u_21, p_u_53, v_u_27))
            v_u_38 = v_u_10:new(p_u_21, p_u_22, p_u_23, p_u_53, v_u_27.PrimaryPart, v_u_27.SearchSurface)
            v_u_39 = v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.AcquireMaterialsInfoSection)
            p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(v_u_39, v_u_39:get_child_part(), v_u_27.AcquireMaterialsInfoSection.NoteMachineButton), p_u_22, function() --[[ Line: 260 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (ref 3): p_u_23, (ref 4): v_u_12, (ref 5): p_u_22 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                p_u_23:remove_all_menus_except(p_u_21._ui_manager:get_hud_ui())
                p_u_23:push_menu(v_u_12:new(p_u_21, p_u_22, p_u_23))
            end))
            p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(v_u_39, v_u_39:get_child_part(), v_u_27.AcquireMaterialsInfoSection.MarketplaceButton), p_u_22, function() --[[ Line: 269 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (ref 3): p_u_23, (ref 4): v_u_9, (ref 5): v_u_13, (ref 6): p_u_22 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                p_u_23:remove_all_menus_except(p_u_21._ui_manager:get_hud_ui())
                if v_u_9.TradeEnabled == true then
                    p_u_23:push_menu(v_u_13:new(p_u_21, p_u_22, p_u_23))
                end;
            end))
            v_u_40 = v_u_5:new(p_u_53, v_u_27.PrimaryPart, v_u_27.CombineSongInfoSection):set_default_sgui()
            v_u_41 = p_u_53:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(v_u_40, v_u_40:get_child_part(), v_u_27.CombineSongInfoSection.SongsButton), p_u_22, function() --[[ Line: 282 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (ref 3): p_u_23, (copy 4): p_u_53, (ref 5): v_u_44, (ref 6): v_u_42, (ref 7): v_u_14, (ref 8): p_u_22 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                p_u_23:remove_all_menus_except(p_u_21._ui_manager:get_hud_ui(), function(p54) --[[ Line: 284 ]]
                    --[[ Upvalues: (ref 1): p_u_53 ]]
                    return p54 == p_u_53;
                end)
                v_u_44 = v_u_42
                p_u_23:push_menu(v_u_14:new(p_u_21, p_u_22, p_u_23, v_u_42))
            end))
            p_u_53:set_combine_song_info_selected_song_key(nil)
            p_u_53:update_current_tab()
            if p_u_25 ~= nil then
                p_u_53:get_current_tab_instance():select_element(p_u_25)
                f_update_amount_buttons()
            end;
            p_u_53:reset_selected_item()
            p_u_53:transition_update_visual(0)
            p_u_53:layout()
        end;
        v_u_26.set_current_tab_and_update = function(p55, p56) --[[ Name: set_current_tab_and_update ]] --[[ Line: 302 ]]
            --[[ Upvalues: (ref 1): v_u_38, (ref 2): p_u_24 ]]
            v_u_38:reset()
            v_u_38:raise_changed()
            p_u_24 = p56
            p55:set_on_refocus_selected_element(nil)
            p55:update_current_tab()
        end;
        v_u_26.update_current_tab = function(p57) --[[ Name: update_current_tab ]] --[[ Line: 309 ]]
            --[[ Upvalues: (copy 1): v_u_30, (ref 2): p_u_24, (copy 3): v_u_31, (ref 4): v_u_1, (ref 5): v_u_28, (ref 6): v_u_32, (ref 7): v_u_33, (ref 8): v_u_38, (ref 9): v_u_43, (copy 10): f_update_amount_buttons ]]
            for v58, v59 in v_u_30:key_itr() do
                v59:set_visible(v58 == p_u_24)
            end;
            for v60, v61 in v_u_31:key_itr() do
                local v62
                if v60 == p_u_24 then
                    v61:get_part().SurfaceGui.ZOffset = 2000 + v61:get_uichild():get_child_id()
                    v62 = 1
                else
                    v61:get_part().SurfaceGui.ZOffset = 1500 + v61:get_uichild():get_child_id()
                    v62 = 0.4
                end;
                v_u_1:list_set_alpha_name(v_u_1:get_list_of_children_of_classname(v61:get_part(), "TextLabel"), {
                    ["TextAlpha"] = v62
                })
                v_u_1:list_set_alpha_name(v_u_1:get_list_of_children_of_classname(v61:get_part(), "ImageLabel"), {
                    ["ImageAlpha"] = v62
                })
                v_u_1:r_set_alpha(v61:get_part(), v_u_28)
            end;
            v_u_32:set_visible(p57:get_current_tab_instance():can_page_up())
            v_u_33:set_visible(p57:get_current_tab_instance():can_page_down())
            local v63 = p57:get_current_tab_instance():is_search_section_enabled()
            v_u_38:set_enabled(v63)
            if v63 == true then
                local v64, v65 = p57:get_current_tab_instance():get_category_names()
                v_u_38:set_category_names(v64, v65)
            end;
            v_u_43.Text = p57:get_current_tab_instance():get_empty_text()
            v_u_43.Visible = false
            p57:get_current_tab_instance():redraw_list()
            f_update_amount_buttons()
        end;
        v_u_26.set_empty_display_visible = function(_, p66) --[[ Name: set_empty_display_visible ]] --[[ Line: 343 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            v_u_43.Visible = p66
        end;
        v_u_26.list_element_pressed = function(p67, p68, p69, p70) --[[ Name: list_element_pressed ]] --[[ Line: 345 ]]
            --[[ Upvalues: (ref 1): v_u_34, (copy 2): v_u_37, (copy 3): f_update_amount_buttons ]]
            v_u_34:set_visible(true)
            v_u_34:set_position_scaled_offset(v_u_37:get(p69):get_pos(), Vector2.new(0, -0.15))
            for v71 = 1, v_u_37:count() do
                local v72 = v_u_37:get(v71)
                if v72 == p68 then
                    v72:set_highlighted(true)
                else
                    v72:set_highlighted(false)
                end;
            end;
            p67:set_combine_song_info_selected_song_key(nil)
            p67:get_current_tab_instance():list_element_pressed(p69, p70)
            f_update_amount_buttons()
        end;
        v_u_26.set_combine_song_info_selected_song_key = function(_, p73) --[[ Name: set_combine_song_info_selected_song_key ]] --[[ Line: 363 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_40, (ref 3): v_u_41 ]]
            v_u_42 = p73
            if v_u_42 == nil then
                v_u_40:set_visible(false)
                v_u_41:set_visible(false)
            else
                v_u_40:set_visible(true)
                v_u_41:set_visible(true)
            end;
        end;
        v_u_26.setup_list_elements = function(p74) --[[ Name: setup_list_elements ]] --[[ Line: 374 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_3, (ref 3): v_u_15, (ref 4): v_u_5, (copy 5): p_u_22, (copy 6): p_u_21, (copy 7): v_u_37 ]]
            local l_InventoryItemProto_0 = v_u_27.InventoryItemProto
            l_InventoryItemProto_0.Parent = nil
            local v75 = v_u_3:new()
            for v76 = 1, 12 do
                v75:push_back(v_u_27.Anchors:FindFirstChild(string.format("Anchor%d", v76)))
            end;
            for v77 = 1, v75:count() do
                local v78 = v75:get(v77)
                local v79 = l_InventoryItemProto_0:Clone()
                v79.Name = string.format("CraftingUIListElement(%d)", v77)
                v79.Parent = v_u_27
                v79.Position = v78.Position
                local v80 = v_u_15:new(v_u_5:new(p74, v_u_27.PrimaryPart, v79), p_u_22, p74, v77)
                p74:add_cycle_element(p_u_21, 1, v80)
                v_u_37:push_back(v80)
            end;
            p74:clear_list()
        end;
        v_u_26.clear_list = function(p81) --[[ Name: clear_list ]] --[[ Line: 405 ]]
            --[[ Upvalues: (copy 1): v_u_37, (ref 2): v_u_34, (copy 3): f_update_amount_buttons ]]
            for v82 = 1, v_u_37:count() do
                v_u_37:get(v82):set_highlighted(false)
                v_u_37:get(v82):set_visible(false)
            end;
            v_u_34:set_visible(false)
            local v83 = p81:get_current_tab_instance()
            if v83 then
                p81:set_combine_song_info_selected_song_key(nil)
                v83:clear_selected_display()
                f_update_amount_buttons()
            end;
        end;
        v_u_26.set_on_refocus_selected_element = function(_, p84) --[[ Name: set_on_refocus_selected_element ]] --[[ Line: 419 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            v_u_44 = p84
        end;
        v_u_26.on_refocus = function(p85) --[[ Name: on_refocus ]] --[[ Line: 423 ]]
            --[[ Upvalues: (ref 1): v_u_44, (copy 2): f_update_amount_buttons ]]
            p85:get_current_tab_instance():reset_page()
            p85:update_current_tab()
            if v_u_44 ~= nil then
                local v86 = v_u_44
                v_u_44 = nil
                p85:get_current_tab_instance():select_element(v86)
                f_update_amount_buttons()
            end;
        end;
        v_u_26.behaviour_update = function(p87, p88, p89) --[[ Name: behaviour_update ]] --[[ Line: 435 ]]
            --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_38 ]]
            p87:behaviour_update_base(p88, p_u_21)
            v_u_38:behaviour_update(p88, p89)
            if v_u_38:raise_changed() then
                p87:get_current_tab_instance():reset_page()
                p87:update_current_tab()
            end;
        end;
        v_u_26.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 445 ]]
            --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_27 ]]
            v_u_38:cleanup()
            v_u_27:Destroy()
        end;
        v_u_26.layout = function(p90) --[[ Name: layout ]] --[[ Line: 450 ]]
            --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_29, (ref 3): v_u_27, (copy 4): v_u_37, (ref 5): v_u_34, (ref 6): v_u_38, (ref 7): v_u_39, (ref 8): v_u_40 ]]
            p90:opt_rescale_to_max_nxy(p_u_22, 0.88, 0.8, v_u_29)
            local v91, v92 = p90:opt_update_cframe_params(p_u_22, {
                ["PositionNXY"] = Vector2.new(0.5, 0.45),
                ["OffsetXYZ"] = p90:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v91 == true then
                v_u_27:SetPrimaryPartCFrame(v92)
            end;
            for v93 = 1, v_u_37:count() do
                v_u_37:get(v93):layout()
            end;
            v_u_34:layout()
            v_u_38:layout()
            v_u_39:layout()
            v_u_40:layout()
        end;
        v_u_26.set_alpha = function(_, p94) --[[ Name: set_alpha ]] --[[ Line: 470 ]]
            --[[ Upvalues: (ref 1): v_u_28, (copy 2): v_u_37, (ref 3): v_u_1, (ref 4): v_u_27 ]]
            if v_u_28 ~= p94 then
                v_u_28 = p94
                for v95 = 1, v_u_37:count() do
                    v_u_37:get(v95):set_parent_alpha(v_u_28)
                end;
                v_u_1:r_set_alpha(v_u_27, v_u_28)
            end;
        end;
        v_u_26.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 479 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v_u_26.set_scale = function(_, p96) --[[ Name: set_scale ]] --[[ Line: 480 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            v_u_29 = p96
        end;
        v_u_26.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 481 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29;
        end;
        v_u_26.get_native_size = function(p97) --[[ Name: get_native_size ]] --[[ Line: 483 ]]
            return p97._native_size;
        end;
        v_u_26.get_size = function(p98) --[[ Name: get_size ]] --[[ Line: 486 ]]
            return p98._size;
        end;
        v_u_26.set_size = function(p99, p100) --[[ Name: set_size ]] --[[ Line: 489 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            p99._size = p100
            v_u_27.PrimaryPart.Size = Vector3.new(p100.X, p100.Y, 0)
        end;
        v_u_26.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 493 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27.PrimaryPart.Position;
        end;
        v_u_26.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 496 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27.PrimaryPart.SurfaceGui;
        end;
        v_u_26.set_showing = function(_, p101) --[[ Name: set_showing ]] --[[ Line: 499 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_8 ]]
            if p101 then
                v_u_27.Parent = v_u_8:get_world_ui_folder()
            else
                v_u_27.Parent = nil
            end;
        end;
        v_u_26:cons()
        return v_u_26;
    end
};
