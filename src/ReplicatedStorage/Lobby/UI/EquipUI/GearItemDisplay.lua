-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_5 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_6 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_7 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_8 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_9 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_10 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_11 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_12 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_13 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_33 = {
    ["set_display_item_empty"] = function(_, p14) --[[ Name: set_display_item_empty ]] --[[ Line: 203 ]]
        p14.ColorSection.Visible = false
        p14.GearPowerSection.Visible = false
        p14.Icon.Visible = false
        p14.SlotIcon.Visible = false
        if p14:FindFirstChild("UpgradeCountDisplay") then
            p14.UpgradeCountDisplay.Text = ""
        end;
        if p14:FindFirstChild("PetVisibleDisplay") then
            p14.PetVisibleDisplay.Visible = false
        end;
    end,
    ["set_display_item_playerblob_ownedid"] = function(_, p15, p16, p17) --[[ Name: set_display_item_playerblob_ownedid ]] --[[ Line: 217 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_3, (copy 3): v_u_8, (copy 4): v_u_9, (copy 5): v_u_7, (copy 6): v_u_5 ]]
        local v18, _ = v_u_6:playerblob_ownedid_to_equipmentid(p16, p17)
        if v18 == nil then
            v_u_3:warnf("GearItemDisplay:set_display_item_playerblob_ownedid cannot find owned_id")
        else
            p15.GearPowerSection.Visible = true
            p15.GearPowerSection.Display.Text = tostring(v_u_6:playerblob_get_ownedid_gearpower(p16, p17))
            local v19 = v_u_6:get_ownedid_upgrade_count(p16, p17)
            if v19 == 0 then
                p15.UpgradeCountDisplay.Text = ""
            else
                p15.UpgradeCountDisplay.Text = string.format("+%d", v19)
            end;
            local v20 = v_u_8:statsdict_base()
            v_u_6:playerblob_apply_ownedid_statsdict(p16, p17, v20)
            local v21 = v_u_8:statsdict_get_ranked_colors(v20)
            v_u_8:ranked_colors_statsdict_filter(v21, v20)
            p15.ColorSection.Visible = true
            v_u_9:render_color_section(p15.ColorSection.PrimaryColorIcon, p15.ColorSection.SecondaryColorIcon, v21)
            local v22 = v_u_7:singleton():get_equipment_for_id(v18)
            if v22 then
                p15.Icon.Visible = true
                p15.Icon.Image = v22:get_icon()
                p15.SlotIcon.Visible = true
                p15.SlotIcon.Image = v_u_5:slot_to_icon_outline(v22:get_avatar_slot())
            end;
            if p15:FindFirstChild("PetVisibleDisplay") then
                p15.PetVisibleDisplay.Visible = false
            end;
        end;
    end,
    ["set_display_item_playerblob_pet_ownedid"] = function(_, p23, p24, p25) --[[ Name: set_display_item_playerblob_pet_ownedid ]] --[[ Line: 254 ]]
        --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_8, (copy 3): v_u_9, (copy 4): v_u_12, (copy 5): v_u_3 ]]
        local v26 = v_u_13:playerblob_get_ownedid_to_ownedpet_dict(p24)
        if v26:contains(p25) == true then
            local v27 = v26:get(p25)
            p23.GearPowerSection.Visible = true
            p23.GearPowerSection.Display.Text = tostring(v_u_13:playerblob_get_pet_ownedid_gearpower(p24, p25))
            local v28 = v_u_8:statsdict_base()
            v_u_13:playerblob_apply_pet_ownedid_statsdict(p24, p25, v28)
            local v29 = v_u_8:statsdict_get_ranked_colors(v28)
            v_u_8:ranked_colors_statsdict_filter(v29, v28)
            p23.ColorSection.Visible = true
            v_u_9:render_color_section(p23.ColorSection.PrimaryColorIcon, p23.ColorSection.SecondaryColorIcon, v29)
            local v30 = v_u_12:singleton():get_data_for_petid(v_u_13:ownedpet_get_petid(v27))
            if v30 then
                p23.Icon.Visible = true
                p23.Icon.Image = v30:get_icon()
                p23.SlotIcon.Visible = true
                p23.SlotIcon.Image = v_u_13:get_pet_icon()
                if p23:FindFirstChild("UpgradeCountDisplay") then
                    p23.UpgradeCountDisplay.Text = string.format("Level %d", v_u_13:ownedpet_get_level(v27))
                end;
                if p23:FindFirstChild("PetVisibleDisplay") then
                    local v31, v32, _ = v_u_13:playerblob_get_display_ownedid_petid(p24)
                    p23.PetVisibleDisplay.Visible = v31 and p25 == v32 and true or false
                    return;
                end;
            else
                p23.Icon.Visible = false
                p23.SlotIcon.Visible = false
                v_u_3:warnf(" GearItemDisplay:set_display_item_playerblob_pet_ownedid pet_data nil(%s)", (tostring(v_u_13:ownedpet_get_petid(v27))))
            end;
        end;
    end
}
v_u_33.new = function(_, p_u_34, p_u_35, _, p_u_36, p_u_37) --[[ Name: new ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_33, (copy 3): v_u_5, (copy 4): v_u_13, (copy 5): v_u_1, (copy 6): v_u_6, (copy 7): v_u_3, (copy 8): v_u_10, (copy 9): v_u_4, (copy 10): v_u_11 ]]
    local v38 = {}
    local v_u_39 = v_u_2:new()
    local v_u_40 = false
    local v_u_41 = nil
    local v_u_42 = nil
    v38.cons = function(_) --[[ Name: cons ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): p_u_37 ]]
        p_u_37:set_default_sgui()
    end;
    v38.is_selected = function(_) --[[ Name: is_selected ]] --[[ Line: 44 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        return v_u_40;
    end;
    local v_u_43 = true
    v38.get_visible = function(_) --[[ Name: get_visible ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        return v_u_43;
    end;
    v38.set_visible = function(p44, p45) --[[ Name: set_visible ]] --[[ Line: 48 ]]
        --[[ Upvalues: (ref 1): v_u_43, (copy 2): p_u_37, (copy 3): v_u_39 ]]
        v_u_43 = p45
        p_u_37:set_visible(p45)
        for v46 = 1, v_u_39:count() do
            if v_u_43 == true then
                if p44:get_displayed_ownedid() == nil and p44:get_displayed_pet_ownedid() == nil then
                    v_u_39:get(v46):set_visible(false)
                else
                    v_u_39:get(v46):set_visible(true)
                end;
            else
                v_u_39:get(v46):set_visible(false)
            end;
        end;
    end;
    v38.get_displayed_ownedid = function(_) --[[ Name: get_displayed_ownedid ]] --[[ Line: 64 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        return v_u_41;
    end;
    v38.get_displayed_pet_ownedid = function(_) --[[ Name: get_displayed_pet_ownedid ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        return v_u_42;
    end;
    v38.set_empty = function(_) --[[ Name: set_empty ]] --[[ Line: 67 ]]
        --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_33, (copy 3): p_u_37, (copy 4): v_u_39 ]]
        v_u_41 = nil
        v_u_33:set_display_item_empty(p_u_37:get_child_part().SurfaceGui.Frame)
        for v47 = 1, v_u_39:count() do
            v_u_39:get(v47):set_visible(false)
        end;
    end;
    v38.set_slot_icon_visible = function(_, p48) --[[ Name: set_slot_icon_visible ]] --[[ Line: 75 ]]
        --[[ Upvalues: (copy 1): p_u_37, (ref 2): v_u_5 ]]
        p_u_37:get_child_part().SurfaceGui.Frame.SlotIcon.Visible = true
        p_u_37:get_child_part().SurfaceGui.Frame.SlotIcon.Image = v_u_5:slot_to_icon_outline(p48)
    end;
    v38.set_slot_icon_visible_pet = function(_) --[[ Name: set_slot_icon_visible_pet ]] --[[ Line: 80 ]]
        --[[ Upvalues: (copy 1): p_u_37, (ref 2): v_u_13 ]]
        p_u_37:get_child_part().SurfaceGui.Frame.SlotIcon.Visible = true
        p_u_37:get_child_part().SurfaceGui.Frame.SlotIcon.Image = v_u_13:get_pet_icon()
    end;
    local v_u_49 = nil
    v38.set_on_display_item_playerblob_ownedid_fn = function(_, p50) --[[ Name: set_on_display_item_playerblob_ownedid_fn ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        v_u_49 = p50
    end;
    v38.set_display_item_playerblob_ownedid = function(p51, p52, p53) --[[ Name: set_display_item_playerblob_ownedid ]] --[[ Line: 90 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_6, (ref 3): v_u_3, (ref 4): v_u_41, (ref 5): v_u_42, (ref 6): v_u_33, (copy 7): p_u_37, (copy 8): v_u_39, (ref 9): v_u_49 ]]
        v_u_1:profilebegin("set_display_item_playerblob_ownedid")
        local v54, _ = v_u_6:playerblob_ownedid_to_equipmentid(p52, p53)
        if v54 == nil then
            v_u_3:warnf("GearItemDisplay:set_display_item_playerblob_ownedid cannot find owned_id")
            return p51:set_visible(false);
        end;
        v_u_41 = p53
        v_u_42 = nil
        v_u_33:set_display_item_playerblob_ownedid(p_u_37:get_child_part().SurfaceGui.Frame, p52, p53)
        for v55 = 1, v_u_39:count() do
            v_u_39:get(v55):set_visible(true)
        end;
        if v_u_49 ~= nil then
            v_u_49(p52, p53)
        end;
        v_u_1:profileend()
    end;
    v38.set_display_item_playerblob_pet_ownedid = function(p56, p57, p58) --[[ Name: set_display_item_playerblob_pet_ownedid ]] --[[ Line: 111 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_41, (ref 3): v_u_13, (ref 4): v_u_3, (ref 5): v_u_42, (ref 6): v_u_33, (copy 7): p_u_37, (copy 8): v_u_39 ]]
        v_u_1:profilebegin("set_display_item_playerblob_pet_ownedid")
        v_u_41 = nil
        if v_u_13:playerblob_get_ownedid_to_ownedpet_dict(p57):contains(p58) ~= true then
            v_u_3:warnf("GearItemDisplay:set_display_item_playerblob_pet_ownedid not found(%s)", p58)
            return p56:set_visible(false);
        end;
        v_u_41 = nil
        v_u_42 = p58
        v_u_33:set_display_item_playerblob_pet_ownedid(p_u_37:get_child_part().SurfaceGui.Frame, p57, p58)
        for v59 = 1, v_u_39:count() do
            v_u_39:get(v59):set_visible(true)
        end;
        v_u_1:profileend()
    end;
    v38.add_child_button = function(_, p60) --[[ Name: add_child_button ]] --[[ Line: 130 ]]
        --[[ Upvalues: (copy 1): v_u_39 ]]
        v_u_39:push_back(p60)
        return p60;
    end;
    v38.behaviour_update = function(p61, p62) --[[ Name: behaviour_update ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_43, (copy 2): p_u_35, (copy 3): v_u_39, (copy 4): p_u_34, (copy 5): p_u_37, (ref 6): v_u_40, (ref 7): v_u_10, (ref 8): v_u_4, (ref 9): v_u_41, (copy 10): p_u_36, (ref 11): v_u_42, (ref 12): v_u_11 ]]
        if v_u_43 == true then
            local v63 = p_u_35:get_cursor_nxy()
            local v64 = false
            for v65 = 1, v_u_39:count() do
                local v66 = v_u_39:get(v65)
                if v66:get_visible() and v66:get_uichild():get_nrect(p_u_35):contains_vec2(v63) then
                    v64 = true
                end;
            end;
            if p_u_34._input:get_has_frame_focused_element() == true then
                v_u_40 = false
            else
                local v67 = p_u_37:get_nrect(p_u_35):contains_vec2(v63)
                if v_u_40 then
                    if v67 == false and v64 == false then
                        v_u_40 = false
                    else
                        p_u_34._input:set_has_frame_focused_element(true)
                    end;
                elseif v67 == true and v64 == false then
                    p_u_34._input:set_has_frame_focused_element(true)
                    v_u_40 = true
                end;
            end;
            if v_u_40 and p_u_34._input:control_just_pressed(v_u_10.KEY_CLICK) then
                p_u_34._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                p61:set_scale(1.25)
                if v_u_41 == nil then
                    if v_u_42 == nil then
                        p_u_36:get_stat_display():set_display_overall_stats()
                    elseif p_u_36:get_stat_display():get_displayed_pet_ownedid() == v_u_42 then
                        p_u_36:get_stat_display():set_display_overall_stats()
                    else
                        p_u_36:get_stat_display():set_display_pet_ownedid(v_u_42)
                    end;
                elseif p_u_36:get_stat_display():get_displayed_ownedid() == v_u_41 then
                    p_u_36:get_stat_display():set_display_overall_stats()
                else
                    p_u_36:get_stat_display():set_display_ownedid(v_u_41)
                end;
            end;
            p_u_37:set_scale(v_u_11:expt_sec(p_u_37:get_scale(), v_u_40 and 1.05 or 1, 0.5, p62))
        end;
    end;
    v38.set_scale = function(_, p68) --[[ Name: set_scale ]] --[[ Line: 191 ]]
        --[[ Upvalues: (copy 1): p_u_37 ]]
        p_u_37:set_scale(p68)
    end;
    v38.layout = function(_) --[[ Name: layout ]] --[[ Line: 195 ]]
        --[[ Upvalues: (copy 1): p_u_37 ]]
        p_u_37:layout()
    end;
    v38:cons()
    return v38;
end;
return v_u_33;
