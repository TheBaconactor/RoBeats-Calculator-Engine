-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:57 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_8 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_10 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearSort)
local v_u_12 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_13 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_14 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.GearSlotIncreaseUtil)
local v_u_17 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.GearItemDisplay)
require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_18 = require(game.ReplicatedStorage.Pets.PetUtils)
local v19 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_20 = nil
local v_u_21 = nil
v19:require_client(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21 ]]
    v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.ColorSelectUI)
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
end)
local v_u_22 = {}
local v_u_23 = v_u_8:get_slot_before_value()
local v_u_24 = ""
local v_u_25 = -1
local v_u_26 = -1
local function _() --[[ Name: is_filter_at_default ]] --[[ Line: 43 ]]
    --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_26 ]]
    local v27
    if v_u_24 == "" and v_u_25 == -1 then
        v27 = v_u_26 == -1
    else
        v27 = false
    end;
    return v27;
end;
local function _() --[[ Name: set_filter_to_default ]] --[[ Line: 46 ]]
    --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_26 ]]
    v_u_24 = ""
    v_u_25 = -1
    v_u_26 = -1
end;
v_u_22.new = function(_, p_u_28, p_u_29, p_u_30, p_u_31, p_u_32) --[[ Name: new ]] --[[ Line: 52 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5, (copy 3): v_u_4, (copy 4): v_u_1, (copy 5): v_u_7, (copy 6): v_u_11, (copy 7): v_u_22, (copy 8): v_u_12, (copy 9): v_u_13, (copy 10): v_u_18, (copy 11): v_u_9, (copy 12): v_u_16, (copy 13): v_u_17, (copy 14): v_u_6, (copy 15): v_u_10, (copy 16): v_u_3, (ref 17): v_u_24, (ref 18): v_u_25, (ref 19): v_u_26 ]]
    local v_u_33 = {}
    local v_u_34 = nil
    local v_u_35 = v_u_2:new()
    local v_u_36 = nil
    local v_u_37 = nil
    local v_u_38 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): p_u_31, (copy 2): p_u_32, (copy 3): p_u_28, (ref 4): v_u_5, (ref 5): v_u_4, (copy 6): p_u_29, (ref 7): v_u_36, (copy 8): v_u_33, (ref 9): v_u_1, (ref 10): v_u_7, (ref 11): v_u_34, (ref 12): v_u_11, (copy 13): v_u_35, (ref 14): v_u_37, (ref 15): v_u_22, (copy 16): p_u_30, (ref 17): v_u_38, (ref 18): v_u_12, (ref 19): v_u_13, (ref 20): v_u_18, (ref 21): v_u_9, (ref 22): v_u_16, (ref 23): v_u_17, (ref 24): v_u_6, (ref 25): v_u_10 ]]
        local l_OwnedItemListDisplay_0 = p_u_31.OwnedItemListDisplay
        local v_u_39 = p_u_32:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_32, p_u_31.PrimaryPart, l_OwnedItemListDisplay_0.ArrowLeft), p_u_29, function() --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_33, (ref 3): v_u_1, (ref 4): p_u_28, (ref 5): v_u_7, (ref 6): v_u_34 ]]
            v_u_36 = v_u_33:get_element_list()
            v_u_1:profilebegin("EquipUIOwnedItemDisplayList:prev_page")
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_34:prev_page()
            v_u_1:profileend()
            v_u_36 = nil
        end))
        local v_u_40 = p_u_32:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_32, p_u_31.PrimaryPart, l_OwnedItemListDisplay_0.ArrowRight), p_u_29, function() --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_33, (ref 3): v_u_1, (ref 4): p_u_28, (ref 5): v_u_7, (ref 6): v_u_34 ]]
            v_u_36 = v_u_33:get_element_list()
            v_u_1:profilebegin("EquipUIOwnedItemDisplayList:next_page")
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_34:next_page()
            v_u_1:profileend()
            v_u_36 = nil
        end))
        local l_OwnedItemSection_0 = p_u_31.MainSurface.SurfaceGui.Frame.LoadedSection.OwnedItemSection
        local l_CurrentPageDisplay_0 = l_OwnedItemSection_0.PageDisplaySection.CurrentPageDisplay
        local l_MaxPageDisplay_0 = l_OwnedItemSection_0.PageDisplaySection.MaxPageDisplay
        local l_EmptyDisplay_0 = l_OwnedItemSection_0.EmptyDisplay
        local l_OwnedGearCountDisplay_0 = l_OwnedItemSection_0.OwnedGearCountDisplay
        local l_OwnedMiniCountDisplay_0 = l_OwnedItemSection_0.OwnedMiniCountDisplay
        local function f_add_sort_toggle_button(p_u_41, p42) --[[ Name: add_sort_toggle_button ]] --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): p_u_28, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): p_u_31, (ref 6): p_u_29, (ref 7): v_u_7, (ref 8): v_u_11, (ref 9): v_u_33, (ref 10): v_u_35 ]]
            v_u_35:add(p_u_41, v_u_5:button_bind_anim_toggle(p_u_32:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_32, p_u_31.PrimaryPart, p42), p_u_29, function() --[[ Line: 103 ]]
                --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_11, (copy 4): p_u_41, (ref 5): v_u_33 ]]
                p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_11:set_sort_type(p_u_41)
                v_u_33:update_display()
            end):set_auto_zoffset_behaviour(true)), function() --[[ Line: 109 ]]
                --[[ Upvalues: (ref 1): p_u_32 ]]
                return p_u_32:get_alpha();
            end))
        end;
        f_add_sort_toggle_button(v_u_11.SortType.Color, l_OwnedItemListDisplay_0.ColorButton)
        f_add_sort_toggle_button(v_u_11.SortType.GearPower, l_OwnedItemListDisplay_0.GearPowerButton)
        f_add_sort_toggle_button(v_u_11.SortType.Slot, l_OwnedItemListDisplay_0.SlotButton)
        v_u_37 = p_u_32:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_32, p_u_31.PrimaryPart, l_OwnedItemListDisplay_0.FilterButton), p_u_29, function() --[[ Line: 118 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_22, (ref 4): p_u_29, (ref 5): p_u_30, (ref 6): v_u_36, (ref 7): v_u_33 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_22:show_filter_menu(p_u_28, p_u_29, p_u_30, function() --[[ Line: 120 ]]
                --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_33 ]]
                v_u_36 = nil
                v_u_33:update_display()
            end)
        end):set_auto_zoffset_behaviour(true))
        v_u_38 = v_u_5:button_bind_anim_toggle(v_u_37, function() --[[ Line: 126 ]]
            --[[ Upvalues: (ref 1): p_u_32 ]]
            return p_u_32:get_alpha();
        end)
        v_u_34 = v_u_12:new():set_fn_get_data_list(function() --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            return v_u_33:get_element_list();
        end):set_fn_set_element_data(function(p43, p44) --[[ Line: 130 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_13, (ref 3): v_u_18 ]]
            if p44 then
                local v45 = p_u_28._player_blob_manager:get_player_blob()
                if v_u_13.DebugMinisActive == true and v_u_18:is_ownedpet(p44) then
                    p43:set_display_item_playerblob_pet_ownedid(v45, v_u_18:ownedpet_get_ownedid(p44))
                else
                    p43:set_display_item_playerblob_ownedid(v45, p44.OwnedID)
                end;
                p43:set_visible(true)
            else
                p43:set_visible(false)
            end;
        end):set_fn_next_prev_visible(function(p46, p47) --[[ Line: 143 ]]
            --[[ Upvalues: (copy 1): v_u_39, (copy 2): v_u_40 ]]
            v_u_39:set_visible(p47)
            v_u_40:set_visible(p46)
        end):set_fn_update_page_display(function(p48, p49) --[[ Line: 147 ]]
            --[[ Upvalues: (copy 1): l_CurrentPageDisplay_0, (copy 2): l_MaxPageDisplay_0, (ref 3): p_u_28, (copy 4): l_OwnedGearCountDisplay_0, (ref 5): v_u_9, (ref 6): v_u_16, (copy 7): l_OwnedMiniCountDisplay_0, (ref 8): v_u_18 ]]
            l_CurrentPageDisplay_0.Text = tostring(p48)
            l_MaxPageDisplay_0.Text = tostring(p49)
            local v50 = p_u_28._player_blob_manager:get_player_blob()
            l_OwnedGearCountDisplay_0.Text = string.format("%d/%d", v_u_9:get_owned_equipment_list(v50):count(), v_u_16:playerblob_get_max_gear_slot_count(v50))
            l_OwnedMiniCountDisplay_0.Text = string.format("%d", v_u_18:playerblob_get_ownedid_to_ownedpet_dict(v50):count())
        end):set_fn_is_empty(function(p51) --[[ Line: 160 ]]
            --[[ Upvalues: (copy 1): l_EmptyDisplay_0 ]]
            l_EmptyDisplay_0.Visible = p51
        end)
        local v52 = {}
        for v53 = 1, 15 do
            local v54 = l_OwnedItemListDisplay_0.Anchors:FindFirstChild((tostring(v53)))
            v54.Parent = nil
            v52[#v52 + 1] = v54
        end;
        local l_Proto_0 = l_OwnedItemListDisplay_0.Proto
        l_Proto_0.Parent = nil
        v_u_34:create_list_elements_from_anchors_and_proto(v52, l_Proto_0, p_u_31, function(p55) --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_32, (ref 3): p_u_31, (ref 4): v_u_17, (ref 5): p_u_28, (ref 6): p_u_29, (ref 7): p_u_30, (ref 8): v_u_5, (ref 9): v_u_7, (ref 10): v_u_13, (ref 11): v_u_18, (ref 12): v_u_9, (ref 13): v_u_6, (ref 14): v_u_10 ]]
            local v56 = v_u_4:new(p_u_32, p_u_31.PrimaryPart, p55.PrimaryPart)
            local v_u_57 = v_u_17:new(p_u_28, p_u_29, p_u_30, p_u_32, v56)
            v_u_57:add_child_button(p_u_32:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v56, p55.PrimaryPart, p55.EquipButton), p_u_29, function() --[[ Line: 185 ]]
                --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_13, (copy 4): v_u_57, (ref 5): v_u_18, (ref 6): p_u_32, (ref 7): v_u_9, (ref 8): v_u_6, (ref 9): v_u_10 ]]
                p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                local v58 = p_u_28._player_blob_manager:get_player_blob()
                if v_u_13.DebugMinisActive == true and v_u_57:get_displayed_pet_ownedid() ~= nil then
                    local v59, v60 = v_u_18:playerblob_equip_pet_ownedid(v58, v_u_57:get_displayed_pet_ownedid())
                    if v59 then
                        p_u_32:get_pet_display():anim_trigger_slot_selected(v60)
                    end;
                else
                    local v61 = v_u_57:get_displayed_ownedid()
                    local v62 = v_u_9:playerblob_ownedid_to_equipmentid(v58, v61)
                    if v62 == nil then
                        return v_u_6:warnf("EquipUIOwnedItemDisplayList EquipButton ownedid(%s) invalid", (tostring(v61)));
                    end;
                    local v63 = v_u_10:singleton():get_equipment_for_id(v62)
                    if v63 then
                        p_u_32:get_equipped_display():anim_trigger_slot_selected(v63:get_avatar_slot())
                        v_u_9:playerblob_equip_ownedid(v58, v61)
                    else
                        v_u_6:warnf("OwnedID(%s) equipmentid(%s) not found", tostring(v61), (tostring(v62)))
                    end;
                end;
                p_u_32:gear_updated_local()
                p_u_32:update_display()
            end)))
            v_u_57:set_visible(false)
            return v_u_57;
        end)
    end;
    v_u_33.anim_trigger_ownedid_unequipped = function(_, p_u_64) --[[ Name: anim_trigger_ownedid_unequipped ]] --[[ Line: 217 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_34 ]]
        v_u_3:for_each(v_u_34:get_display_elements(), function(p65) --[[ Line: 218 ]]
            --[[ Upvalues: (copy 1): p_u_64 ]]
            if p65:get_visible() and p65:get_displayed_ownedid() == p_u_64 then
                p65:set_scale(1.25)
                return false;
            end;
        end)
    end;
    v_u_33.anim_trigger_pet_ownedid_unequipped = function(_, p_u_66) --[[ Name: anim_trigger_pet_ownedid_unequipped ]] --[[ Line: 226 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_34 ]]
        v_u_3:for_each(v_u_34:get_display_elements(), function(p67) --[[ Line: 227 ]]
            --[[ Upvalues: (copy 1): p_u_66 ]]
            if p67:get_visible() and p67:get_displayed_pet_ownedid() == p_u_66 then
                p67:set_scale(1.25)
                return false;
            end;
        end)
    end;
    v_u_33.get_element_list = function(_) --[[ Name: get_element_list ]] --[[ Line: 235 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_1, (copy 3): p_u_28, (ref 4): v_u_9, (ref 5): v_u_18, (ref 6): v_u_24, (ref 7): v_u_10, (ref 8): v_u_11, (ref 9): v_u_25, (ref 10): v_u_26, (ref 11): v_u_3 ]]
        if v_u_36 ~= nil then
            return v_u_36;
        end;
        v_u_1:profilebegin("EquipUIOwnedItemDisplayList:get_element_list")
        local v_u_68 = p_u_28._player_blob_manager:get_player_blob()
        local v69 = v_u_9:get_owned_equipment_list(v_u_68)
        for _, v70 in v_u_18:playerblob_get_ownedid_to_ownedpet_dict(v_u_68):key_itr() do
            v69:push_back(v70)
        end;
        local v_u_71
        if #v_u_24 > 0 then
            v_u_71 = string.lower(v_u_24)
        else
            v_u_71 = nil
        end;
        local v_u_72 = v_u_9:playerblob_ownedid_to_equipmentid_dict(v_u_68)
        v_u_1:profilebegin("remove_if")
        v69:remove_if(function(p73) --[[ Line: 252 ]]
            --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_72, (ref 3): v_u_10, (ref 4): v_u_71, (ref 5): v_u_11, (copy 6): v_u_68, (ref 7): v_u_25, (ref 8): v_u_26, (ref 9): v_u_1, (ref 10): v_u_9 ]]
            local v74 = v_u_18:is_ownedpet(p73)
            if v74 then
                if v_u_18:ownedpet_get_petid(p73) == nil then
                    return true;
                end;
            elseif v_u_10:singleton():get_equipment_for_id((v_u_72:get(p73.OwnedID))) == nil then
                return true;
            end;
            if v_u_71 == nil or string.find(string.lower((v_u_11:owned_data_get_name(v_u_68, p73))), v_u_71, 1, true) ~= nil then
                if v_u_25 == -1 or v_u_11:owned_data_get_slot(v_u_68, p73) == v_u_25 then
                    if v_u_26 == -1 or v_u_11:owned_data_get_color(v_u_68, p73) == v_u_26 then
                        if v74 then
                            v_u_1:profilebegin("playerblob_pet_ownedid_is_equipped")
                            local v75 = v_u_18:playerblob_pet_ownedid_is_equipped(v_u_68, v_u_18:ownedpet_get_ownedid(p73))
                            v_u_1:profileend()
                            return v75;
                        else
                            v_u_1:profilebegin("ownedid_is_equipped")
                            local v76 = v_u_9:ownedid_is_equipped(v_u_68, p73.OwnedID)
                            v_u_1:profileend()
                            return v76;
                        end;
                    else
                        return true;
                    end;
                else
                    return true;
                end;
            else
                return true;
            end;
        end)
        v_u_1:profileend()
        v_u_1:profilebegin("sort")
        v_u_3:sort_fast(v69, v_u_11:get_sort_fn_for_playerblob(v_u_68))
        v_u_1:profileend()
        v_u_1:profileend()
        return v69;
    end;
    v_u_33.update_display = function(p77) --[[ Name: update_display ]] --[[ Line: 316 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_24, (ref 3): v_u_25, (ref 4): v_u_26, (ref 5): v_u_36, (ref 6): v_u_34, (copy 7): v_u_35, (ref 8): v_u_11 ]]
        local v78 = v_u_38
        local v79
        if v_u_24 == "" and v_u_25 == -1 then
            v79 = v_u_26 == -1
        else
            v79 = false
        end;
        v78:set_toggle(v79 ~= true)
        v_u_36 = p77:get_element_list()
        v_u_34:page_update()
        for v80, v81 in v_u_35:key_itr() do
            v81:set_toggle(v_u_11:get_sort_type() == v80)
        end;
        v_u_36 = nil
    end;
    v_u_33.behaviour_update = function(_, p_u_82) --[[ Name: behaviour_update ]] --[[ Line: 329 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_34 ]]
        v_u_3:for_each(v_u_34:get_display_elements(), function(p83) --[[ Line: 330 ]]
            --[[ Upvalues: (copy 1): p_u_82 ]]
            p83:behaviour_update(p_u_82)
        end)
    end;
    v_u_33.layout = function(_) --[[ Name: layout ]] --[[ Line: 335 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        v_u_34:layout()
    end;
    f_cons()
    return v_u_33;
end;
v_u_22.show_filter_menu = function(_, p_u_84, p_u_85, p_u_86, p_u_87) --[[ Name: show_filter_menu ]] --[[ Line: 343 ]]
    --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_1, (ref 3): v_u_24, (ref 4): v_u_25, (copy 5): v_u_23, (copy 6): v_u_18, (copy 7): v_u_8, (ref 8): v_u_26, (copy 9): v_u_14, (copy 10): v_u_15, (ref 11): v_u_20 ]]
    local v_u_88 = nil
    v_u_88 = p_u_84._menus:push_menu(v_u_21:new(p_u_84, p_u_85, p_u_86, function(p89) --[[ Line: 355 ]]
        p89:set_header_text("Filter By...")
        p89:get_element_list():push_back_table_list({
            0,
            1,
            2,
            3
        })
    end, function(p90, p91, p92, _, _) --[[ Line: 364 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_24, (ref 3): v_u_25, (ref 4): v_u_23, (ref 5): v_u_18, (ref 6): v_u_8, (ref 7): v_u_26, (ref 8): v_u_14 ]]
        if p90 == 0 then
            p91.Text = "Clear Filters"
            p92.Image = v_u_1:gear_assetid()
            return;
        elseif p90 == 1 then
            if #v_u_24 == 0 then
                p91.Text = "Name"
                p92.Image = v_u_1:get_question_assetid()
            else
                p91.Text = string.format("Name: %s", v_u_24)
                p92.Image = v_u_1:important_assetid()
            end;
        elseif p90 == 2 then
            if v_u_25 == -1 then
                p91.Text = "Slot"
                p92.Image = v_u_1:get_question_assetid()
                return;
            elseif v_u_25 == v_u_23 then
                p91.Text = "Slot: Minis"
                p92.Image = v_u_18:get_pet_icon()
            else
                p91.Text = string.format("Slot: %s", v_u_8:slot_to_name(v_u_25))
                p92.Image = v_u_8:slot_to_icon_outline(v_u_25)
            end;
        else
            if p90 == 3 then
                if v_u_26 == -1 then
                    p91.Text = "Color"
                    p92.Image = v_u_1:get_question_assetid()
                    return;
                end;
                p91.Text = string.format("Color: %s", v_u_14:color_to_name(v_u_26))
                p92.Image = v_u_14:color_to_iconimage(v_u_26)
            end;
            return;
        end;
    end, function(p93) --[[ Line: 402 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_26, (copy 4): p_u_87, (copy 5): p_u_86, (ref 6): v_u_88, (copy 7): p_u_84, (ref 8): v_u_15, (copy 9): p_u_85, (ref 10): v_u_21, (ref 11): v_u_8, (ref 12): v_u_23, (ref 13): v_u_18, (ref 14): v_u_20, (ref 15): v_u_14 ]]
        if p93 == 0 then
            v_u_24 = ""
            v_u_25 = -1
            v_u_26 = -1
            p_u_87()
            p_u_86:remove_menu(v_u_88)
            return;
        elseif p93 == 1 then
            p_u_84._menus:push_menu(v_u_15:new(p_u_84, p_u_85, p_u_86, "Enter Name", "Enter name to filter by.", function(p94) --[[ Line: 410 ]]
                --[[ Upvalues: (ref 1): v_u_24, (ref 2): p_u_87 ]]
                v_u_24 = p94
                p_u_87()
            end):set_text(v_u_24):set_empty_message("(Text)"))
            return;
        elseif p93 == 2 then
            p_u_84._menus:push_menu(v_u_21:new(p_u_84, p_u_85, p_u_86, function(p95) --[[ Line: 423 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_23 ]]
                p95:set_header_text("Select Slot")
                p95:get_element_list():push_back_table_list({
                    v_u_8.SHIRT,
                    v_u_8.PANTS,
                    v_u_8.HAT,
                    v_u_8.FACE,
                    v_u_8.NECK,
                    v_u_8.BACK,
                    v_u_23
                })
            end, function(p96, p97, p98, _, _) --[[ Line: 435 ]]
                --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_18, (ref 3): v_u_8 ]]
                if p96 == v_u_23 then
                    p97.Text = "Minis"
                    p98.Image = v_u_18:get_pet_icon()
                else
                    p97.Text = v_u_8:slot_to_name(p96)
                    p98.Image = v_u_8:slot_to_icon_outline(p96)
                end;
            end, function(p99) --[[ Line: 444 ]]
                --[[ Upvalues: (ref 1): v_u_25, (ref 2): p_u_87 ]]
                if p99 ~= nil then
                    v_u_25 = p99
                    p_u_87()
                end;
            end))
        elseif p93 == 3 then
            p_u_84._menus:push_menu(v_u_20:new(p_u_84, p_u_85, p_u_86, "Select Color", "Select color to filter by.", function(p100) --[[ Line: 459 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_26, (ref 3): p_u_87 ]]
                if p100 ~= v_u_14:color_none() then
                    v_u_26 = p100
                    p_u_87()
                end;
            end))
        end;
    end)):set_refresh_on_refocus(true)
end;
return v_u_22;
