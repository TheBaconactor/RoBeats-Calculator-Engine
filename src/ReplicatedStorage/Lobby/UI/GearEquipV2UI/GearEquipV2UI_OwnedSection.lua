-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.SPUIButton)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_10 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.GearSelectUI)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearSort)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v14 = {}
local v_u_31 = {
    ["new"] = function(_, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7, (copy 3): v_u_10, (copy 4): v_u_9 ]]
        local v19 = {}
        local v_u_20 = nil
        local v_u_21 = v_u_3:new()
        v19.get_uichild = function(_) --[[ Name: get_uichild ]] --[[ Line: 31 ]]
            --[[ Upvalues: (copy 1): p_u_16 ]]
            return p_u_16;
        end;
        v19.add_child_uibutton = function(_, p22) --[[ Name: add_child_uibutton ]] --[[ Line: 32 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            v_u_21:push_back(p22)
        end;
        v19.set_owned_obj = function(p23, p24) --[[ Name: set_owned_obj ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_18, (copy 3): p_u_15 ]]
            v_u_20 = p24.OwnedID
            p_u_18:set_owned_obj(p_u_15._player_blob_manager:get_player_blob(), v_u_20)
            p23:set_buttons_visible(true)
        end;
        v19.set_empty = function(p25) --[[ Name: set_empty ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_18 ]]
            v_u_20 = nil
            p_u_18:set_hidden()
            p25:set_buttons_visible(false)
        end;
        v19.equip_action = function(_) --[[ Name: equip_action ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_7, (copy 3): p_u_15, (ref 4): v_u_10, (ref 5): v_u_9, (copy 6): p_u_17 ]]
            if v_u_20 == nil then
                v_u_7:warnf("GearEquipUI_OwnedSection.EquipElement:equip_action() _current_ownedid is nil")
            end;
            local v26 = p_u_15._player_blob_manager:get_player_blob()
            p_u_17:get_equipped_section():anim_trigger_slot_selected((v_u_10:singleton():get_equipment_for_id(v_u_9:playerblob_ownedid_to_equipmentid(v26, v_u_20)):get_avatar_slot()))
            v_u_9:playerblob_equip_ownedid(v26, v_u_20)
            p_u_17:gear_updated_local()
            p_u_17:refresh_ui()
        end;
        v19.layout = function(_) --[[ Name: layout ]] --[[ Line: 61 ]]
            --[[ Upvalues: (copy 1): p_u_16, (copy 2): v_u_21 ]]
            p_u_16:layout()
            for v27 = 1, v_u_21:count() do
                v_u_21:get(v27):layout()
            end;
        end;
        v19.set_buttons_visible = function(_, p28) --[[ Name: set_buttons_visible ]] --[[ Line: 68 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            for v29 = 1, v_u_21:count() do
                v_u_21:get(v29):set_visible(p28)
            end;
        end;
        v19.visual_update = function(_, p30, _) --[[ Name: visual_update ]] --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): p_u_18 ]]
            p_u_18:visual_update(p30)
        end;
        return v19;
    end
}
v14.new = function(_, p_u_32, p_u_33, p_u_34, p_u_35) --[[ Name: new ]] --[[ Line: 81 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_6, (copy 5): v_u_5, (copy 6): v_u_8, (copy 7): v_u_12, (copy 8): v_u_11, (copy 9): v_u_1, (copy 10): v_u_9, (copy 11): v_u_31, (copy 12): v_u_13 ]]
    local v_u_36 = v_u_4:SPUIObjectBase()
    local v_u_37 = 1
    local v_u_38 = 1
    local v_u_39 = v_u_3:new()
    local v_u_40 = 0
    local v_u_41 = nil
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = nil
    local v_u_45 = v_u_2:new()
    v_u_36.cons = function(p_u_46) --[[ Name: cons ]] --[[ Line: 98 ]]
        --[[ Upvalues: (copy 1): p_u_35, (ref 2): v_u_43, (copy 3): p_u_34, (copy 4): p_u_32, (ref 5): v_u_6, (ref 6): v_u_5, (copy 7): p_u_33, (ref 8): v_u_8, (ref 9): v_u_41, (copy 10): v_u_39, (ref 11): v_u_42, (ref 12): v_u_44, (copy 13): v_u_45, (ref 14): v_u_12 ]]
        p_u_46._native_size = p_u_35.PrimaryPart.Size
        p_u_46._size = p_u_46._native_size
        v_u_43 = p_u_35.OwnedSurface.SurfaceGui.Frame.Title
        p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(p_u_46, p_u_35.PrimaryPart, p_u_35.BackButtonSurface), p_u_33, function() --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): p_u_34 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            p_u_34:back_action()
        end))
        v_u_41 = p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(p_u_46, p_u_35.PrimaryPart, p_u_35.TopArrowSurface), p_u_33, function() --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (copy 3): p_u_46, (ref 4): v_u_39 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_46:increment_owned_list_offset(-v_u_39:count())
        end))
        v_u_42 = p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(p_u_46, p_u_35.PrimaryPart, p_u_35.BottomArrowSurface), p_u_33, function() --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (copy 3): p_u_46, (ref 4): v_u_39 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_46:increment_owned_list_offset(v_u_39:count())
        end))
        v_u_44 = v_u_5:new(p_u_46, p_u_35.PrimaryPart, p_u_35.SearchSurface)
        v_u_45:add(v_u_12.SortType.Slot, p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_44, p_u_35.PrimaryPart, p_u_35.SearchSurface.SortCategory3Button), p_u_33, function() --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_12, (copy 4): p_u_46 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_12:set_sort_type(v_u_12.SortType.Slot)
            p_u_46:update_ui_elements()
        end)))
        v_u_45:add(v_u_12.SortType.Upgrades, p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_44, p_u_35.PrimaryPart, p_u_35.SearchSurface.SortCategory4Button), p_u_33, function() --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_12, (copy 4): p_u_46 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_12:set_sort_type(v_u_12.SortType.Upgrades)
            p_u_46:update_ui_elements()
        end)))
        v_u_45:add(v_u_12.SortType.Name, p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_44, p_u_35.PrimaryPart, p_u_35.SearchSurface.SortCategory1Button), p_u_33, function() --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_12, (copy 4): p_u_46 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_12:set_sort_type(v_u_12.SortType.Name)
            p_u_46:update_ui_elements()
        end)))
        v_u_45:add(v_u_12.SortType.GearPower, p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_44, p_u_35.PrimaryPart, p_u_35.SearchSurface.SortCategory2Button), p_u_33, function() --[[ Line: 166 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_12, (copy 4): p_u_46 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_12:set_sort_type(v_u_12.SortType.GearPower)
            p_u_46:update_ui_elements()
        end)))
        p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_44, p_u_35.PrimaryPart, p_u_35.SearchSurface.TrashButton), p_u_33, function() --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (copy 3): p_u_46 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_46:delete_gear_pressed()
        end))
        p_u_46:create_ui()
        p_u_46:update_ui_elements()
    end;
    v_u_36.delete_gear_pressed = function(p_u_47) --[[ Name: delete_gear_pressed ]] --[[ Line: 186 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_32, (copy 3): p_u_33 ]]
        v_u_11:show_delete_gear_menu(p_u_32, p_u_33, function() --[[ Line: 187 ]]
            --[[ Upvalues: (copy 1): p_u_47 ]]
            p_u_47:update_ui_elements()
        end)
    end;
    v_u_36.increment_owned_list_offset = function(p48, p49) --[[ Name: increment_owned_list_offset ]] --[[ Line: 192 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        v_u_40 = v_u_40 + p49
        p48:update_ui_elements()
    end;
    v_u_36.refresh_ui = function(p50) --[[ Name: refresh_ui ]] --[[ Line: 197 ]]
        p50:update_ui_elements()
    end;
    local function f_set_image_children_alpha(p51, p52) --[[ Name: set_image_children_alpha ]] --[[ Line: 201 ]]
        --[[ Upvalues: (copy 1): v_u_36, (ref 2): v_u_1 ]]
        local v53 = p52 * v_u_36:get_alpha()
        local v54 = v_u_1:get_list_of_children_of_classname(p51, "ImageLabel")
        for v55 = 1, v54:count() do
            local v56 = v54:get(v55)
            v56.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = v53
            }, "ImageLabel")
            v56.ImageTransparency = v_u_1:tra(v53)
        end;
    end;
    v_u_36.update_sort_button_alphas = function(_) --[[ Name: update_sort_button_alphas ]] --[[ Line: 211 ]]
        --[[ Upvalues: (copy 1): v_u_45, (ref 2): v_u_12, (copy 3): f_set_image_children_alpha ]]
        for v57, v58 in v_u_45:key_itr() do
            if v57 == v_u_12:get_sort_type() then
                v58:set_scale(1)
                f_set_image_children_alpha(v58:get_part(), 1)
            else
                v58:set_scale(0.8)
                f_set_image_children_alpha(v58:get_part(), 0.2)
            end;
        end;
    end;
    v_u_36.update_ui_elements = function(p59) --[[ Name: update_ui_elements ]] --[[ Line: 224 ]]
        --[[ Upvalues: (copy 1): p_u_32, (ref 2): v_u_9, (ref 3): v_u_12, (ref 4): v_u_40, (copy 5): v_u_39, (ref 6): v_u_43, (ref 7): v_u_41, (ref 8): v_u_42 ]]
        p59:update_sort_button_alphas()
        local v_u_60 = p_u_32._player_blob_manager:get_player_blob()
        local v61 = v_u_9:get_owned_equipment_list(v_u_60)
        v61:remove_if(function(p62) --[[ Line: 229 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): v_u_60 ]]
            return v_u_9:ownedid_is_equipped(v_u_60, p62.OwnedID);
        end)
        v61:sort(v_u_12:get_sort_fn_for_playerblob(v_u_60))
        if v_u_40 >= v61:count() then
            v_u_40 = v61:count() - v_u_39:count()
        end;
        if v_u_40 < 0 then
            v_u_40 = 0
        end;
        if v61:count() == 0 then
            v_u_43.Text = "Owned (None)"
        else
            v_u_43.Text = string.format("Owned (%d of %d)", math.floor(v_u_40 / v_u_39:count()) + 1, math.floor((v61:count() - 1) / v_u_39:count()) + 1)
        end;
        for v63 = 1, v_u_39:count() do
            local v64 = v_u_39:get(v63)
            local v65 = v63 + v_u_40
            if v65 <= v61:count() then
                v64:set_owned_obj(v61:get(v65))
            else
                v64:set_empty()
            end;
        end;
        if v_u_40 == 0 then
            v_u_41:set_visible(false)
        else
            v_u_41:set_visible(true)
        end;
        if v_u_40 + v_u_39:count() >= v61:count() then
            v_u_42:set_visible(false)
        else
            v_u_42:set_visible(true)
        end;
    end;
    v_u_36.create_ui = function(p66) --[[ Name: create_ui ]] --[[ Line: 273 ]]
        --[[ Upvalues: (copy 1): p_u_35, (ref 2): v_u_31, (copy 3): p_u_32, (ref 4): v_u_5, (copy 5): p_u_34, (ref 6): v_u_13, (ref 7): v_u_6, (copy 8): p_u_33, (ref 9): v_u_8, (copy 10): v_u_39 ]]
        local l_GearElementProto_0 = p_u_35.GearElementProto
        l_GearElementProto_0.Parent = nil
        for v67 = 1, 6 do
            local l_Anchors_0 = p_u_35.Anchors[tostring(v67)]
            local v68 = l_GearElementProto_0:Clone()
            local v_u_69 = v_u_31:new(p_u_32, v_u_5:new(p66, p_u_35.PrimaryPart, v68), p_u_34, v_u_13:new(v68):set_stat_icon_left_margin(1))
            v_u_69:add_child_uibutton(p_u_34:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_69:get_uichild(), v_u_69:get_uichild():get_child_part(), v68.EquipButton), p_u_33, function() --[[ Line: 291 ]]
                --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (copy 3): v_u_69 ]]
                p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                v_u_69:equip_action()
            end)))
            v_u_69:get_uichild():set_position(l_Anchors_0.Position)
            v68.Parent = p_u_35
            v_u_39:push_back(v_u_69)
        end;
    end;
    v_u_36.layout = function(p70) --[[ Name: layout ]] --[[ Line: 303 ]]
        --[[ Upvalues: (copy 1): p_u_33, (ref 2): v_u_38, (copy 3): p_u_35, (copy 4): v_u_39, (ref 5): v_u_44 ]]
        p70:opt_rescale_to_max_nxy(p_u_33, 0.36, 0.85, v_u_38)
        local v71, v72 = p70:opt_update_cframe_params(p_u_33, {
            ["PositionNXY"] = Vector2.new(1, 0.5),
            ["OffsetXYZ"] = p70:anchored_offset(1, 0.5) + Vector3.new(p_u_33:get_size_from_nxy(-0.015, 0).X),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v71 == true then
            p_u_35:SetPrimaryPartCFrame(v72)
        end;
        for v73 = 1, v_u_39:count() do
            v_u_39:get(v73):layout()
        end;
        v_u_44:layout()
    end;
    v_u_36.visual_update = function(_, p74, p75) --[[ Name: visual_update ]] --[[ Line: 321 ]]
        --[[ Upvalues: (copy 1): v_u_39 ]]
        for v76 = 1, v_u_39:count() do
            v_u_39:get(v76):visual_update(p74, p75)
        end;
    end;
    v_u_36.set_alpha = function(p77, p78) --[[ Name: set_alpha ]] --[[ Line: 327 ]]
        --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_1, (copy 3): p_u_35 ]]
        if v_u_37 ~= p78 then
            v_u_37 = p78
            p77:update_sort_button_alphas()
            v_u_1:r_set_alpha(p_u_35, v_u_37)
        end;
    end;
    v_u_36.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 334 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37;
    end;
    v_u_36.set_scale = function(_, p79) --[[ Name: set_scale ]] --[[ Line: 335 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        v_u_38 = p79
    end;
    v_u_36.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 336 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38;
    end;
    v_u_36.get_native_size = function(p80) --[[ Name: get_native_size ]] --[[ Line: 338 ]]
        return p80._native_size;
    end;
    v_u_36.get_size = function(p81) --[[ Name: get_size ]] --[[ Line: 341 ]]
        return p81._size;
    end;
    v_u_36.set_size = function(p82, p83) --[[ Name: set_size ]] --[[ Line: 344 ]]
        --[[ Upvalues: (copy 1): p_u_35 ]]
        p82._size = p83
        p_u_35.PrimaryPart.Size = Vector3.new(p83.X, p83.Y, 0)
    end;
    v_u_36.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 348 ]]
        --[[ Upvalues: (copy 1): p_u_35 ]]
        return p_u_35.PrimaryPart.Position;
    end;
    v_u_36.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 351 ]]
        --[[ Upvalues: (copy 1): p_u_35 ]]
        return p_u_35.PrimaryPart.SurfaceGui;
    end;
    v_u_36:cons()
    return v_u_36;
end;
return v14;
