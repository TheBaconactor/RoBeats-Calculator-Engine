-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:45 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_11 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.GearSelectUI)
local v_u_13 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_14 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_15 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.GearSlotIncreaseUtil)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_18 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_19 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
local v_u_20 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.CharacterDisplaySection)
local v_u_21 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.EquipUIOwnedItemDisplayList)
local v_u_22 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.EquipUIStatDisplay)
local v_u_23 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.EquipUIEquippedDisplay)
local v_u_24 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.EquipUILoadoutDisplay)
local v_u_25 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.EquipUIPetDisplay)
local v26 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_27 = nil
local v_u_28 = nil
local v_u_29 = nil
local v_u_30 = nil
v26:require_client(function() --[[ Line: 39 ]]
    --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_28, (ref 3): v_u_29, (ref 4): v_u_30 ]]
    v_u_27 = require(game.ReplicatedStorage.Lobby.Menus.CraftingUI)
    v_u_28 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabGearUpgrades)
    v_u_29 = require(game.ReplicatedStorage.Lobby.Menus.GearShopUI)
    v_u_30 = require(game.ReplicatedStorage.Lobby.Menus.ColorSelectUI)
end)
return {
    ["new"] = function(_, p_u_31, p_u_32, p_u_33) --[[ Name: new ]] --[[ Line: 48 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_11, (copy 3): v_u_15, (copy 4): v_u_1, (copy 5): v_u_8, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_6, (ref 9): v_u_29, (copy 10): v_u_12, (ref 11): v_u_27, (ref 12): v_u_28, (copy 13): v_u_16, (copy 14): v_u_9, (copy 15): v_u_17, (copy 16): v_u_7, (copy 17): v_u_18, (copy 18): v_u_19, (copy 19): v_u_20, (copy 20): v_u_21, (copy 21): v_u_23, (copy 22): v_u_22, (copy 23): v_u_24, (copy 24): v_u_14, (copy 25): v_u_25, (copy 26): v_u_2, (ref 27): v_u_30, (copy 28): v_u_13, (copy 29): v_u_10 ]]
        local v_u_34 = v_u_3:new(p_u_32, p_u_33)
        local v_u_35 = nil
        local v_u_36 = 1
        local v_u_37 = 1
        local v_u_38 = nil
        local v_u_39 = nil
        local v_u_40 = nil
        local v_u_41 = nil
        local v_u_42 = nil
        local v_u_43 = nil
        local v_u_44 = nil
        local v_u_45 = nil
        local function _() --[[ Name: snapshot_initial_state ]] --[[ Line: 65 ]]
            --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_44, (ref 3): v_u_11, (ref 4): v_u_45, (ref 5): v_u_15 ]]
            local v46 = p_u_31._player_blob_manager:get_player_blob()
            v_u_44 = v_u_11:playerblob_get_equipdict(v46)
            v_u_45 = v_u_15:playerblob_get_slot_to_owned_pet_dict(v46)
        end;
        v_u_34.get_equipped_display = function(_) --[[ Name: get_equipped_display ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            return v_u_41;
        end;
        v_u_34.get_owned_item_display = function(_) --[[ Name: get_owned_item_display ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            return v_u_39;
        end;
        v_u_34.get_stat_display = function(_) --[[ Name: get_stat_display ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_40 ]]
            return v_u_40;
        end;
        v_u_34.get_pet_display = function(_) --[[ Name: get_pet_display ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            return v_u_43;
        end;
        local v_u_47 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_1, (ref 3): v_u_8, (copy 4): v_u_34, (copy 5): p_u_31, (ref 6): v_u_44, (ref 7): v_u_11, (ref 8): v_u_45, (ref 9): v_u_15, (ref 10): v_u_5, (ref 11): v_u_4, (copy 12): p_u_32, (ref 13): v_u_6, (copy 14): p_u_33, (ref 15): v_u_29, (ref 16): v_u_12, (ref 17): v_u_27, (ref 18): v_u_28, (ref 19): v_u_47, (ref 20): v_u_16, (ref 21): v_u_9, (ref 22): v_u_17, (ref 23): v_u_7, (ref 24): v_u_18, (ref 25): v_u_19, (ref 26): v_u_38, (ref 27): v_u_20, (ref 28): v_u_39, (ref 29): v_u_21, (ref 30): v_u_41, (ref 31): v_u_23, (ref 32): v_u_40, (ref 33): v_u_22, (ref 34): v_u_42, (ref 35): v_u_24, (ref 36): v_u_14, (ref 37): v_u_43, (ref 38): v_u_25 ]]
            v_u_35 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Gear.EquipUI:Clone()
            v_u_35.Name = v_u_1:gen_name(v_u_35.Name)
            v_u_35.Parent = v_u_8:get_world_ui_folder()
            v_u_34._native_size = v_u_35.PrimaryPart.Size
            v_u_34._size = v_u_34._native_size
            local v48 = p_u_31._player_blob_manager:get_player_blob()
            v_u_44 = v_u_11:playerblob_get_equipdict(v48)
            v_u_45 = v_u_15:playerblob_get_slot_to_owned_pet_dict(v48)
            v_u_34:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_34, v_u_35.PrimaryPart, v_u_35.BackButtonSurface), p_u_32, function() --[[ Line: 91 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_6, (ref 3): p_u_33, (ref 4): v_u_34 ]]
                p_u_31._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
                p_u_33:remove_menu(v_u_34)
                v_u_34:save_equip_changes()
            end))
            v_u_34:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_34, v_u_35.PrimaryPart, v_u_35.Buttons.AutoEquipButton), p_u_32, function() --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_6, (ref 3): v_u_34 ]]
                p_u_31._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                v_u_34:auto_equip_button_pressed()
            end)):set_auto_zoffset_behaviour(true)
            v_u_34:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_34, v_u_35.PrimaryPart, v_u_35.Buttons.BuyButton), p_u_32, function() --[[ Line: 110 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_6, (ref 3): p_u_33, (ref 4): v_u_34, (ref 5): v_u_29, (ref 6): p_u_32 ]]
                p_u_31._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                p_u_33:remove_all_menus_except(p_u_31._ui_manager:get_hud_ui(), function(p49) --[[ Line: 112 ]]
                    --[[ Upvalues: (ref 1): v_u_34 ]]
                    return p49 == v_u_34;
                end)
                v_u_34:save_equip_changes(function() --[[ Line: 113 ]]
                    --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_29, (ref 3): p_u_31, (ref 4): p_u_32 ]]
                    p_u_33:push_menu(v_u_29:new(p_u_31, p_u_32, p_u_33))
                end)
            end)):set_auto_zoffset_behaviour(true)
            v_u_34:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_34, v_u_35.PrimaryPart, v_u_35.Buttons.TrashButton), p_u_32, function() --[[ Line: 122 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_6, (ref 3): v_u_34, (ref 4): v_u_12, (ref 5): p_u_32 ]]
                p_u_31._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                v_u_34:save_equip_changes(function() --[[ Line: 124 ]]
                    --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_31, (ref 3): p_u_32 ]]
                    v_u_12:show_delete_gear_menu(p_u_31, p_u_32)
                end)
            end)):set_auto_zoffset_behaviour(true)
            v_u_34:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_34, v_u_35.PrimaryPart, v_u_35.Buttons.UpgradeButton), p_u_32, function() --[[ Line: 133 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_6, (ref 3): p_u_33, (ref 4): v_u_34, (ref 5): v_u_27, (ref 6): v_u_28 ]]
                p_u_31._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                p_u_33:remove_all_menus_except(p_u_31._ui_manager:get_hud_ui(), function(p50) --[[ Line: 135 ]]
                    --[[ Upvalues: (ref 1): v_u_34 ]]
                    return p50 == v_u_34;
                end)
                v_u_34:save_equip_changes(function() --[[ Line: 136 ]]
                    --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_27, (ref 3): v_u_28 ]]
                    p_u_31._menus:push_menu(v_u_27:new(p_u_31, p_u_31._spui, p_u_31._menus, v_u_28.Tab))
                end)
            end)):set_auto_zoffset_behaviour(true)
            v_u_34:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_34, v_u_35.PrimaryPart, v_u_35.Buttons.EditUpgradeButton), p_u_32, function() --[[ Line: 145 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_6, (ref 3): v_u_34, (ref 4): v_u_12, (ref 5): p_u_32 ]]
                p_u_31._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                v_u_34:save_equip_changes(function() --[[ Line: 147 ]]
                    --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_31, (ref 3): p_u_32 ]]
                    v_u_12:show_upgrade_edit_menu(p_u_31, p_u_32)
                end)
            end)):set_auto_zoffset_behaviour(true)
            v_u_47 = v_u_34:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_34, v_u_35.PrimaryPart, v_u_35.Buttons.IncreaseGearSlotsButton), p_u_32, function() --[[ Line: 156 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_6, (ref 3): v_u_34, (ref 4): v_u_16, (ref 5): p_u_33, (ref 6): v_u_9, (ref 7): p_u_32, (ref 8): v_u_17, (ref 9): v_u_7, (ref 10): v_u_18, (ref 11): v_u_19 ]]
                p_u_31._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                v_u_34:save_equip_changes(function() --[[ Line: 158 ]]
                    --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_16, (ref 3): p_u_33, (ref 4): v_u_9, (ref 5): p_u_32, (ref 6): v_u_17, (ref 7): v_u_7, (ref 8): v_u_6, (ref 9): v_u_18, (ref 10): v_u_19 ]]
                    local v_u_51 = p_u_31._player_blob_manager:get_player_blob()
                    if v_u_16:can_playerblob_increase_level(v_u_51) == true then
                        local v_u_52 = v_u_16:playerblob_get_gear_slot_increase_level(v_u_51)
                        local v_u_53 = v_u_52 + 1
                        local v_u_54, v_u_55 = v_u_16:get_currency_to_next_level(v_u_52)
                        p_u_33:push_menu(v_u_9:new(p_u_31, p_u_32, p_u_33):set_text("Confirm", string.format("Do you want to increase your maximum number of gear from %d to %d? This will cost %d %s. (You currently have %d %s)", v_u_16:get_level_to_max_gear_slot_count(v_u_52), v_u_16:get_level_to_max_gear_slot_count(v_u_53), v_u_54, v_u_17:currency_type_to_string(v_u_55), v_u_17:get_currency_type_amount(v_u_51, v_u_55), v_u_17:currency_type_to_string(v_u_55))):set_okay_button_fn(function() --[[ Line: 179 ]]
                            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_9, (ref 3): p_u_31, (ref 4): p_u_32, (ref 5): v_u_7, (ref 6): v_u_6, (ref 7): v_u_16, (copy 8): v_u_52, (copy 9): v_u_53, (ref 10): v_u_18, (ref 11): v_u_19, (copy 12): v_u_51, (copy 13): v_u_55, (copy 14): v_u_54 ]]
                            local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 181 ]]
                                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_9, (ref 3): p_u_31, (ref 4): p_u_32, (ref 5): v_u_7, (ref 6): v_u_6, (ref 7): v_u_16, (ref 8): v_u_52, (ref 9): v_u_53, (ref 10): v_u_18 ]]
                                local v_u_56 = p_u_33:push_menu(v_u_9:new(p_u_31, p_u_32, p_u_33):set_text("Loading...", ""):set_close_button_visible(false))
                                p_u_31._evt:wait_on_event_once(v_u_7.EVT_Lobby_ServerResponseIncreaseGearSlotLevel, function(p57, p58, p_u_59) --[[ Line: 183 ]]
                                    --[[ Upvalues: (ref 1): p_u_33, (copy 2): v_u_56, (ref 3): v_u_9, (ref 4): p_u_31, (ref 5): p_u_32, (ref 6): v_u_6, (ref 7): v_u_16, (ref 8): v_u_52, (ref 9): v_u_53, (ref 10): v_u_18 ]]
                                    if p57 == true then
                                        p_u_31._player_blob_manager:do_sync(function() --[[ Line: 189 ]]
                                            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_56, (ref 3): p_u_31, (ref 4): v_u_6, (ref 5): v_u_16, (ref 6): v_u_52, (ref 7): v_u_53, (ref 8): v_u_18, (copy 9): p_u_59, (ref 10): v_u_9, (ref 11): p_u_32 ]]
                                            p_u_33:remove_menu(v_u_56)
                                            p_u_31._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                                            local v60 = string.format("Your maximum number of gear has been increased from %d to %d!", v_u_16:get_level_to_max_gear_slot_count(v_u_52), v_u_16:get_level_to_max_gear_slot_count(v_u_53))
                                            local v61 = v_u_18.RewardInfo:table_to_list(p_u_59)
                                            if v61:count() > 0 then
                                                v60 = v60 .. "\n" .. v_u_18:generate_description_from_rewardinfo_list(v61)
                                            end;
                                            p_u_33:push_menu(v_u_9:new(p_u_31, p_u_32, p_u_33):set_text("Success", v60))
                                        end)
                                    else
                                        p_u_33:remove_menu(v_u_56)
                                        p_u_33:push_menu(v_u_9:new(p_u_31, p_u_32, p_u_33):set_text("Failed", p58))
                                    end;
                                end)
                                p_u_31._evt:fire_event_to_server(v_u_7.EVT_Lobby_ClientRequestIncreaseGearSlotLevel)
                            end;
                            local v62 = v_u_19:playerblob_purchase_needs_redirect(v_u_51, v_u_55, v_u_54)
                            if v62:is_valid() then
                                v_u_19:show_purchase_redirect(p_u_31, v62, function(p63) --[[ Line: 211 ]]
                                    --[[ Upvalues: (copy 1): f_do_purchase ]]
                                    if p63 then
                                        f_do_purchase()
                                    end;
                                end)
                            else
                                f_do_purchase()
                            end;
                        end))
                    end;
                end)
            end)):set_auto_zoffset_behaviour(true)
            v_u_5:button_add_enabled_anim(v_u_47, function() --[[ Line: 226 ]]
                --[[ Upvalues: (ref 1): v_u_34 ]]
                return v_u_34:get_alpha();
            end)
            v_u_38 = v_u_20:new(p_u_31, p_u_32, v_u_4:new(v_u_34, v_u_35.PrimaryPart, v_u_35.RenderCharacterSurface), v_u_35.RenderCharacterSurface.SurfaceGui)
            v_u_38:update_from_playerblob((p_u_31._player_blob_manager:get_player_blob()))
            v_u_39 = v_u_21:new(p_u_31, p_u_32, p_u_33, v_u_35, v_u_34)
            v_u_41 = v_u_23:new(p_u_31, p_u_32, p_u_33, v_u_35, v_u_34)
            v_u_40 = v_u_22:new(p_u_31, p_u_32, p_u_33, v_u_35, v_u_34)
            v_u_42 = v_u_24:new(p_u_31, p_u_32, p_u_33, v_u_35, v_u_34)
            if v_u_14.DebugMinisActive == true then
                v_u_43 = v_u_25:new(p_u_31, p_u_32, p_u_33, v_u_35, v_u_34)
            end;
            v_u_34:update_display()
            v_u_42:match_initial_selected_loadout()
            v_u_34:transition_update_visual(0)
            v_u_34:layout()
        end;
        v_u_34.animate_equip_for_playerblob_change = function(p64, p65) --[[ Name: animate_equip_for_playerblob_change ]] --[[ Line: 254 ]]
            --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_2, (ref 3): v_u_11, (ref 4): v_u_15 ]]
            local v66 = p_u_31._player_blob_manager:get_player_blob()
            local v67 = v_u_2:new()
            local v68 = v_u_2:new()
            for _, v69 in v_u_11:playerblob_slot_to_equippedobj_dict(v66):key_itr() do
                v67:push_back(v69.OwnedID)
            end;
            for _, v70 in v_u_15:playerblob_get_slot_to_owned_pet_dict(v66):key_itr() do
                v68:push_back(v_u_15:ownedpet_get_ownedid(v70))
            end;
            p65(v66)
            local v71 = v_u_2:new()
            local v72 = v_u_2:new()
            for v73, _ in v_u_11:playerblob_slot_to_equippedobj_dict(v66):key_itr() do
                v71:push_back(v73)
            end;
            for v74, _ in v_u_15:playerblob_get_slot_to_owned_pet_dict(v66):key_itr() do
                v72:push_back(v74)
            end;
            p64:gear_updated_local()
            p64:update_display()
            for v75 = 1, v67:count() do
                p64:get_owned_item_display():anim_trigger_ownedid_unequipped(v67:get(v75))
            end;
            for _, v76 in v68:key_itr() do
                p64:get_owned_item_display():anim_trigger_pet_ownedid_unequipped(v76)
            end;
            for v77 = 1, v71:count() do
                p64:get_equipped_display():anim_trigger_slot_selected(v71:get(v77))
            end;
            for _, v78 in v72:key_itr() do
                p64:get_pet_display():anim_trigger_slot_selected(v78)
            end;
        end;
        v_u_34.auto_equip_button_pressed = function(p_u_79) --[[ Name: auto_equip_button_pressed ]] --[[ Line: 305 ]]
            --[[ Upvalues: (copy 1): p_u_33, (ref 2): v_u_30, (copy 3): p_u_31, (copy 4): p_u_32, (ref 5): v_u_2, (ref 6): v_u_13, (ref 7): v_u_11 ]]
            p_u_33:push_menu(v_u_30:new(p_u_31, p_u_32, p_u_33, "Select Primary Element", "Select the primary element you want your gear to be optimized for.", function(p_u_80) --[[ Line: 309 ]]
                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_30, (ref 3): p_u_31, (ref 4): p_u_32, (copy 5): p_u_79, (ref 6): v_u_2, (ref 7): v_u_13, (ref 8): v_u_11 ]]
                p_u_33:push_menu(v_u_30:new(p_u_31, p_u_32, p_u_33, "Select Secondary Element", "(Optional) Select the secondary element you want your gear to be optimized for.", function(p_u_81) --[[ Line: 313 ]]
                    --[[ Upvalues: (ref 1): p_u_79, (ref 2): v_u_2, (copy 3): p_u_80, (ref 4): v_u_13, (ref 5): v_u_11 ]]
                    p_u_79:animate_equip_for_playerblob_change(function(p82) --[[ Line: 314 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_80, (copy 3): p_u_81, (ref 4): v_u_13, (ref 5): v_u_11 ]]
                        local v83 = v_u_2:new()
                        v83:push_back(p_u_80)
                        if p_u_81 ~= v_u_13:color_none() and p_u_81 ~= p_u_80 then
                            v83:push_back(p_u_81)
                        end;
                        v_u_11:playerblob_autoequip_for_colors(p82, v83)
                    end)
                end):set_none_selectable():set_color_button_visible(p_u_80, false))
            end))
        end;
        v_u_34.save_equip_changes = function(_, p_u_84) --[[ Name: save_equip_changes ]] --[[ Line: 328 ]]
            --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_11, (ref 3): v_u_15, (ref 4): v_u_42, (ref 5): v_u_44, (ref 6): v_u_45, (copy 7): p_u_33, (ref 8): v_u_9, (copy 9): p_u_32, (ref 10): v_u_7 ]]
            local v85 = p_u_31._player_blob_manager:get_player_blob()
            if v_u_42:has_loadout_change() == false and (v_u_11:cmp_equipdicts(v_u_11:playerblob_get_equipdict(v85), v_u_44) == true and v_u_15:cmp_slot_to_ownedpet_dict(v_u_45, (v_u_15:playerblob_get_slot_to_owned_pet_dict(v85))) == true) then
                if p_u_84 then
                    p_u_84()
                end;
            else
                local v_u_86 = p_u_33:push_menu(v_u_9:new(p_u_31, p_u_32, p_u_33):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
                p_u_31._evt:wait_on_event_once(v_u_7.EVT_Lobby_ServerAcknowledgeCharacterUpdateEquipped, function(p_u_87, p_u_88) --[[ Line: 340 ]]
                    --[[ Upvalues: (ref 1): p_u_31, (ref 2): p_u_33, (copy 3): v_u_86, (ref 4): v_u_44, (ref 5): v_u_11, (ref 6): v_u_45, (ref 7): v_u_15, (ref 8): v_u_42, (copy 9): p_u_84, (ref 10): v_u_9, (ref 11): p_u_32 ]]
                    p_u_31._player_blob_manager:do_sync(function(_) --[[ Line: 341 ]]
                        --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_86, (ref 3): p_u_31, (ref 4): v_u_44, (ref 5): v_u_11, (ref 6): v_u_45, (ref 7): v_u_15, (ref 8): v_u_42, (ref 9): p_u_84, (copy 10): p_u_87, (ref 11): v_u_9, (ref 12): p_u_32, (copy 13): p_u_88 ]]
                        p_u_33:remove_menu(v_u_86)
                        local v89 = p_u_31._player_blob_manager:get_player_blob()
                        v_u_44 = v_u_11:playerblob_get_equipdict(v89)
                        v_u_45 = v_u_15:playerblob_get_slot_to_owned_pet_dict(v89)
                        v_u_42:clear_loadout_change()
                        if p_u_84 then
                            p_u_84()
                        end;
                        if p_u_87 == false then
                            p_u_33:push_menu(v_u_9:new(p_u_31, p_u_32, p_u_33):set_text("Error", p_u_88))
                        end;
                    end)
                end)
                p_u_31._evt:fire_event_to_server(v_u_7.EVT_Lobby_ClientNotifyCharacterUpdateEquipped, v85.Equipped, v85.Loadouts, v85.EquippedPets, true)
            end;
        end;
        v_u_34.gear_updated_local = function(_) --[[ Name: gear_updated_local ]] --[[ Line: 360 ]]
            --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_38, (ref 3): v_u_42 ]]
            local v90 = p_u_31._player_blob_manager:get_player_blob()
            v_u_38:update_from_playerblob(v90)
            v_u_42:update_from_playerblob(v90)
        end;
        v_u_34.update_display = function(_) --[[ Name: update_display ]] --[[ Line: 366 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_41, (ref 3): v_u_40, (ref 4): v_u_42, (ref 5): v_u_43, (ref 6): v_u_47, (ref 7): v_u_16, (copy 8): p_u_31 ]]
            v_u_39:update_display()
            v_u_41:update_display()
            if v_u_40:get_displayed_ownedid() == nil then
                if v_u_40:get_displayed_pet_ownedid() == nil then
                    v_u_40:set_display_overall_stats()
                else
                    v_u_40:set_display_pet_ownedid(v_u_40:get_displayed_pet_ownedid())
                end;
            else
                v_u_40:set_display_ownedid(v_u_40:get_displayed_ownedid())
            end;
            v_u_42:update_display()
            if v_u_43 then
                v_u_43:update_display()
            end;
            v_u_47:set_enabled(v_u_16:can_playerblob_increase_level(p_u_31._player_blob_manager:get_player_blob()))
        end;
        v_u_34.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 386 ]]
            --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_38 ]]
            v_u_35:Destroy()
            v_u_38:teardown()
        end;
        v_u_34.on_refocus = function(p91) --[[ Name: on_refocus ]] --[[ Line: 391 ]]
            --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_38 ]]
            v_u_38:update_from_playerblob((p_u_31._player_blob_manager:get_player_blob()))
            p91:update_display()
        end;
        v_u_34.behaviour_update = function(p92, p93, _) --[[ Name: behaviour_update ]] --[[ Line: 397 ]]
            --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_10, (ref 3): v_u_39, (ref 4): v_u_41, (ref 5): v_u_38, (ref 6): v_u_43 ]]
            p92:behaviour_update_base(p93, p_u_31)
            if p92._current_mode == v_u_10.MODE_OPEN then
                v_u_39:behaviour_update(p93)
                v_u_41:behaviour_update(p93)
                v_u_38:behaviour_update(p93)
                if v_u_43 then
                    v_u_43:behaviour_update(p93)
                end;
            end;
        end;
        v_u_34.layout = function(p94) --[[ Name: layout ]] --[[ Line: 409 ]]
            --[[ Upvalues: (copy 1): p_u_32, (ref 2): v_u_37, (ref 3): v_u_35, (ref 4): v_u_38, (ref 5): v_u_39, (ref 6): v_u_41, (ref 7): v_u_43 ]]
            p94:opt_rescale_to_max_nxy(p_u_32, 0.9, 0.9, v_u_37)
            local v95, v96 = p94:opt_update_cframe_params(p_u_32, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p94:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v95 == true then
                v_u_35:SetPrimaryPartCFrame(v96)
            end;
            v_u_38:layout()
            v_u_39:layout()
            v_u_41:layout()
            if v_u_43 then
                v_u_43:layout()
            end;
        end;
        v_u_34.set_alpha = function(_, p97) --[[ Name: set_alpha ]] --[[ Line: 428 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_1, (ref 3): v_u_35, (ref 4): v_u_38 ]]
            if v_u_36 ~= p97 then
                v_u_36 = p97
                v_u_1:r_set_alpha(v_u_35, v_u_36)
                v_u_38:set_alpha(v_u_36)
            end;
        end;
        v_u_34.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 435 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36;
        end;
        v_u_34.set_scale = function(_, p98) --[[ Name: set_scale ]] --[[ Line: 436 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            v_u_37 = p98
        end;
        v_u_34.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 437 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37;
        end;
        v_u_34.get_native_size = function(p99) --[[ Name: get_native_size ]] --[[ Line: 439 ]]
            return p99._native_size;
        end;
        v_u_34.get_size = function(p100) --[[ Name: get_size ]] --[[ Line: 442 ]]
            return p100._size;
        end;
        v_u_34.set_size = function(p101, p102) --[[ Name: set_size ]] --[[ Line: 445 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            p101._size = p102
            v_u_35.PrimaryPart.Size = Vector3.new(p102.X, p102.Y, 0)
        end;
        v_u_34.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 449 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            return v_u_35.PrimaryPart.Position;
        end;
        v_u_34.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 452 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            return v_u_35.PrimaryPart.SurfaceGui;
        end;
        v_u_34.set_showing = function(_, p103) --[[ Name: set_showing ]] --[[ Line: 455 ]]
            --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_35, (ref 3): v_u_8 ]]
            v_u_38:set_showing(p103)
            if p103 then
                v_u_35.Parent = v_u_8:get_world_ui_folder()
            else
                v_u_35.Parent = nil
            end;
        end;
        f_cons()
        return v_u_34;
    end
};
