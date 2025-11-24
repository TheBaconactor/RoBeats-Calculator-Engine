-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.LocalWeldAccessories)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_10 = {}
local v_u_11 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 14 ]]
        return {
            ["ShirtSlotClearDefaultShirt"] = true,
            ["PantsSlotClearDefaultPants"] = true,
            ["HasHair"] = false
        };
    end
}
local function f_character_copy_instances_of_classname(p12, p13, p14) --[[ Name: character_copy_instances_of_classname ]] --[[ Line: 24 ]]
    for _, v15 in pairs(p13:GetChildren()) do
        if v15.ClassName == p14 then
            v15:Clone().Parent = p12
        end;
    end;
end;
v_u_10.character_modify_with_equipped_data = function(_, p_u_16, p17, p18, p_u_19) --[[ Name: character_modify_with_equipped_data ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_6, (copy 3): v_u_5, (copy 4): v_u_4, (copy 5): v_u_7, (copy 6): v_u_9, (copy 7): v_u_11, (copy 8): v_u_2, (copy 9): v_u_1, (copy 10): v_u_10, (copy 11): f_character_copy_instances_of_classname ]]
    if v_u_8.PrintBlobOnGet == true then
        v_u_6:puts("SPAvatarUtil:character_modify_with_equipped_data(%s)", v_u_5:table_to_string(p18))
    end;
    local v20 = v_u_4:new()
    if v_u_8.CharacterModifyAnchorSmartAnchor == true and p_u_16.PrimaryPart then
        p_u_16.PrimaryPart.Anchored = true
    end;
    local v_u_21 = 0
    v_u_7:set_start_end_fns(function() --[[ Line: 48 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21 = v_u_21 + 1
    end, function() --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21 = v_u_21 - 1
    end)
    local function _(p22) --[[ Name: resolve_equipment_id ]] --[[ Line: 54 ]]
        --[[ Upvalues: (ref 1): v_u_9 ]]
        local l_EquipmentID_0 = p22.EquipmentID
        local l_OAID_0 = p22.OAID
        if typeof(l_OAID_0) == "number" then
            if l_OAID_0 == v_u_9:get_override_appearance_default_id() then
                l_OAID_0 = l_EquipmentID_0
            end;
        else
            l_OAID_0 = l_EquipmentID_0
        end;
        return l_OAID_0;
    end;
    local v23 = v_u_11:new()
    local v_u_24 = v_u_21
    for v25 = 1, #p18 do
        local v26 = p18[v25]
        local l_EquipmentID_1 = v26.EquipmentID
        local l_OAID_1 = v26.OAID
        if typeof(l_OAID_1) == "number" then
            if l_OAID_1 == v_u_9:get_override_appearance_default_id() then
                l_OAID_1 = l_EquipmentID_1
            end;
        else
            l_OAID_1 = l_EquipmentID_1
        end;
        if l_OAID_1 ~= nil then
            local v27 = v_u_2:singleton():get_equipment_for_id(l_OAID_1)
            if v27 then
                v20:add(v27:get_avatar_slot(), v26)
                v27:modify_equip_data_params(v23)
            else
                v_u_6:warnf("SPAvatarUtil:character_modify_with_equipped_data skipping invalid equipmentid(%s)", (tostring(l_OAID_1)))
            end;
        end;
    end;
    for _, v28 in v_u_1:slot_itr() do
        v_u_10:slot_remove_wearing(v28, p_u_16, v23, v23)
    end;
    v_u_10:remove_accessories_of_attachment_name(p_u_16, "HairAttachment")
    if v23.HasHair ~= true then
        v_u_10:character_copy_accessories_of_attachment_name(p_u_16, p17, "HairAttachment")
    end;
    if v23.ShirtSlotClearDefaultShirt ~= true then
        local v29 = v_u_5:first_child_of_type(p_u_16, "Shirt")
        if v29 then
            v29:Destroy()
        end;
        f_character_copy_instances_of_classname(p_u_16, p17, "Shirt")
    end;
    if v23.PantsSlotClearDefaultPants ~= true then
        local v30 = v_u_5:first_child_of_type(p_u_16, "Pants")
        if v30 then
            v30:Destroy()
        end;
        f_character_copy_instances_of_classname(p_u_16, p17, "Pants")
    end;
    for _, v31 in v_u_1:slot_itr() do
        if v20:get(v31) == nil then
            v_u_10:slot_copy_from_source_character(v31, p_u_16, p17, v23)
        end;
    end;
    if v_u_5:get_list_of_children_of_classname(p_u_16, "Accessory"):count() > 30 then
        if p_u_19 then
            p_u_19()
        end;
        return v_u_6:warnf("SPAvatarUtil:character_modify_with_equipped_data character has over limit of accessories, not equipping");
    end;
    for _, v32 in v_u_1:slot_itr() do
        local v33 = v20:get(v32)
        if v33 ~= nil then
            local v34 = v_u_2:singleton()
            local l_EquipmentID_2 = v33.EquipmentID
            local l_OAID_2 = v33.OAID
            if typeof(l_OAID_2) == "number" then
                if l_OAID_2 == v_u_9:get_override_appearance_default_id() then
                    l_OAID_2 = l_EquipmentID_2
                end;
            else
                l_OAID_2 = l_EquipmentID_2
            end;
            local v35 = v34:get_equipment_for_id(l_OAID_2)
            if v35 == nil then
                v_u_6:warnf("SPAvatarUtil:character_copy_with_equipment_data equipment is nil for(%s)", (tostring(v33.EquipmentID)))
                break;
            end;
            if v35:get_avatar_slot() ~= v32 then
                v_u_6:warnf("SPAvatarUtil:character_copy_with_equipment_data mismatch get_avatar_slot(%s) slot_key(%s)", tostring(v35:get_avatar_slot()), (tostring(v32)))
                break;
            end;
            if v33.Visible == true then
                if v35:requires_apply_appearance_async() then
                    local v36 = v_u_7:get_start_fn()
                    local v_u_37 = v_u_7:get_end_fn()
                    if v36 then
                        v36()
                    end;
                    v35:apply_appearance_async(p_u_16, function() --[[ Line: 139 ]]
                        --[[ Upvalues: (copy 1): v_u_37 ]]
                        if v_u_37 then
                            v_u_37()
                        end;
                    end)
                else
                    v35:apply_appearance(p_u_16)
                end;
            else
                v_u_10:slot_copy_from_source_character(v32, p_u_16, p17, v23)
            end;
        end;
    end;
    if v_u_8.CharacterModifyAnchorSmartAnchor == true then
        spawn(function() --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_6, (copy 3): p_u_16, (copy 4): p_u_19 ]]
            local v38 = 0
            while v_u_24 > 0 do
                v38 = v38 + 0.1
                if v38 > 1.5 then
                    v_u_6:warnf("SPAvatarUtil:character_modify_with_equipped_data waited over 1.5 seconds but did not finish, unanchoring (%s)", p_u_16.Name)
                    break;
                end;
                wait(0.1)
            end;
            if p_u_16.PrimaryPart then
                p_u_16.PrimaryPart.Anchored = false
            end;
            if p_u_19 then
                p_u_19()
            end;
        end)
    end;
    v_u_7:set_start_end_fns(nil, nil)
end;
local function f_remove_children_of_classname(p39, p40) --[[ Name: remove_children_of_classname ]] --[[ Line: 174 ]]
    for _, v41 in pairs(p39:GetChildren()) do
        if v41.ClassName == p40 then
            v41.Parent = nil
            v41:Destroy()
        end;
    end;
end;
local function f_remove_accessories_of_attachment_name(p42, p43) --[[ Name: remove_accessories_of_attachment_name ]] --[[ Line: 183 ]]
    for _, v44 in pairs(p42:GetChildren()) do
        if v44.ClassName == "Accessory" and v44:FindFirstChild("Handle") ~= nil then
            local v45 = false
            for _, v46 in pairs(v44.Handle:GetChildren()) do
                if v46.ClassName == "Attachment" and v46.Name == p43 then
                    v45 = true
                    break;
                end;
            end;
            if v45 == true then
                v44.Parent = nil
                v44:Destroy()
            end;
        end;
    end;
end;
v_u_10.slot_remove_wearing = function(_, p47, p48, p49) --[[ Name: slot_remove_wearing ]] --[[ Line: 202 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): f_remove_children_of_classname, (copy 3): f_remove_accessories_of_attachment_name ]]
    if p47 == v_u_1.SHIRT then
        if p49.ShirtSlotClearDefaultShirt == true then
            f_remove_children_of_classname(p48, "Shirt")
        end;
        f_remove_accessories_of_attachment_name(p48, "BodyFrontAttachment")
        f_remove_accessories_of_attachment_name(p48, "LeftWristRigAttachment")
        f_remove_accessories_of_attachment_name(p48, "RightWristRigAttachment")
        f_remove_accessories_of_attachment_name(p48, "LeftShoulderRigAttachment")
        f_remove_accessories_of_attachment_name(p48, "RightShoulderRigAttachment")
        f_remove_accessories_of_attachment_name(p48, "LeftElbowRigAttachment")
        f_remove_accessories_of_attachment_name(p48, "RightElbowRigAttachment")
        return;
    elseif p47 == v_u_1.PANTS then
        if p49.PantsSlotClearDefaultPants == true then
            f_remove_children_of_classname(p48, "Pants")
        end;
        f_remove_accessories_of_attachment_name(p48, "RightAnkleRigAttachment")
        f_remove_accessories_of_attachment_name(p48, "LeftAnkleRigAttachment")
        f_remove_accessories_of_attachment_name(p48, "WaistCenterAttachment")
    elseif p47 == v_u_1.HAT then
        f_remove_accessories_of_attachment_name(p48, v_u_1:slot_to_attachment_name(p47))
        if p49.HasHair == true then
            f_remove_accessories_of_attachment_name(p48, "HairAttachment")
            return;
        end;
    else
        if p47 == v_u_1.FACE then
            f_remove_accessories_of_attachment_name(p48, v_u_1:slot_to_attachment_name(p47))
            f_remove_accessories_of_attachment_name(p48, "FaceCenterAttachment")
            return;
        end;
        if p47 == v_u_1.NECK then
            f_remove_accessories_of_attachment_name(p48, v_u_1:slot_to_attachment_name(p47))
            return;
        end;
        if p47 == v_u_1.BACK then
            f_remove_accessories_of_attachment_name(p48, v_u_1:slot_to_attachment_name(p47))
            f_remove_accessories_of_attachment_name(p48, "WaistFrontAttachment")
            f_remove_accessories_of_attachment_name(p48, "WaistCenterAttachment")
            f_remove_accessories_of_attachment_name(p48, "LeftShoulderRigAttachment")
            f_remove_accessories_of_attachment_name(p48, "RightShoulderRigAttachment")
        end;
    end;
end;
v_u_10.remove_accessories_of_attachment_name = function(_, p50, p51) --[[ Name: remove_accessories_of_attachment_name ]] --[[ Line: 241 ]]
    --[[ Upvalues: (copy 1): f_remove_accessories_of_attachment_name ]]
    f_remove_accessories_of_attachment_name(p50, p51)
end;
local function f_get_accessories_of_attachment_name(p52, p53, p54) --[[ Name: get_accessories_of_attachment_name ]] --[[ Line: 245 ]]
    for _, v55 in pairs(p52:GetChildren()) do
        if v55.ClassName == "Accessory" and v55:FindFirstChild("Handle") ~= nil then
            local v56 = false
            for _, v57 in pairs(v55.Handle:GetChildren()) do
                if v57.ClassName == "Attachment" and v57.Name == p53 then
                    v56 = true
                    break;
                end;
            end;
            if v56 == true then
                p54:push_back(v55)
            end;
        end;
    end;
end;
local function f_character_copy_accessories_of_attachment_name(p58, p59, p60) --[[ Name: character_copy_accessories_of_attachment_name ]] --[[ Line: 263 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_6, (copy 3): v_u_3, (copy 4): f_get_accessories_of_attachment_name, (copy 5): v_u_8, (copy 6): v_u_7 ]]
    local v_u_61 = v_u_5:get_character_humanoid(p58)
    if v_u_61 == nil then
        return v_u_6:warnf("character_copy_accessories_of_attachment_name(%s) no humanoid");
    end;
    local v62 = v_u_3:new()
    f_get_accessories_of_attachment_name(p59, p60, v62)
    for v63 = 1, v62:count() do
        local v64 = v62:get(v63)
        if v_u_5:get_list_of_children_of_classname(v64, "WrapLayer"):count() > 0 then
            if v_u_8.AllowLayeredClothing == true then
                local v_u_65 = v64:Clone()
                local v_u_66 = v_u_65:FindFirstChild("Handle")
                local function _(p67) --[[ Name: set_handle_alpha ]] --[[ Line: 280 ]]
                    --[[ Upvalues: (copy 1): v_u_66, (ref 2): v_u_5 ]]
                    if v_u_66 then
                        v_u_66.Transparency = v_u_5:tra(p67)
                    end;
                end;
                if v_u_66 then
                    v_u_66.Transparency = v_u_5:tra(0)
                end;
                v_u_7:apply(p58, v_u_65, function() --[[ Line: 286 ]]
                    --[[ Upvalues: (copy 1): v_u_65, (copy 2): v_u_61, (copy 3): v_u_66, (ref 4): v_u_5 ]]
                    v_u_65.Parent = nil
                    v_u_61:AddAccessory(v_u_65)
                    if v_u_66 then
                        v_u_66.Transparency = v_u_5:tra(1)
                    end;
                end)
            end;
        else
            v_u_7:apply(p58, (v64:Clone()))
        end;
    end;
end;
v_u_10.slot_copy_from_source_character = function(_, p68, p69, p70, p71) --[[ Name: slot_copy_from_source_character ]] --[[ Line: 300 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): f_character_copy_instances_of_classname, (copy 3): f_character_copy_accessories_of_attachment_name ]]
    if p68 == v_u_1.SHIRT then
        if p71.ShirtSlotClearDefaultShirt == true then
            f_character_copy_instances_of_classname(p69, p70, "Shirt")
        end;
        f_character_copy_accessories_of_attachment_name(p69, p70, "BodyFrontAttachment")
        f_character_copy_accessories_of_attachment_name(p69, p70, "LeftWristRigAttachment")
        f_character_copy_accessories_of_attachment_name(p69, p70, "RightWristRigAttachment")
        f_character_copy_accessories_of_attachment_name(p69, p70, "LeftShoulderRigAttachment")
        f_character_copy_accessories_of_attachment_name(p69, p70, "RightShoulderRigAttachment")
        f_character_copy_accessories_of_attachment_name(p69, p70, "LeftElbowRigAttachment")
        f_character_copy_accessories_of_attachment_name(p69, p70, "RightElbowRigAttachment")
        return;
    elseif p68 == v_u_1.PANTS then
        if p71.PantsSlotClearDefaultPants == true then
            f_character_copy_instances_of_classname(p69, p70, "Pants")
        end;
        f_character_copy_accessories_of_attachment_name(p69, p70, "WaistCenterAttachment")
    elseif p68 == v_u_1.HAT then
        f_character_copy_accessories_of_attachment_name(p69, p70, v_u_1:slot_to_attachment_name(p68))
        if p71.HasHair == true then
            f_character_copy_accessories_of_attachment_name(p69, p70, "HairAttachment")
            return;
        end;
    else
        if p68 == v_u_1.FACE then
            f_character_copy_accessories_of_attachment_name(p69, p70, v_u_1:slot_to_attachment_name(p68))
            f_character_copy_accessories_of_attachment_name(p69, p70, "FaceCenterAttachment")
            return;
        end;
        if p68 == v_u_1.NECK then
            f_character_copy_accessories_of_attachment_name(p69, p70, v_u_1:slot_to_attachment_name(p68))
            return;
        end;
        if p68 == v_u_1.BACK then
            f_character_copy_accessories_of_attachment_name(p69, p70, v_u_1:slot_to_attachment_name(p68))
            f_character_copy_accessories_of_attachment_name(p69, p70, "WaistFrontAttachment")
        end;
    end;
end;
v_u_10.character_copy_accessories_of_attachment_name = function(_, p72, p73, p74) --[[ Name: character_copy_accessories_of_attachment_name ]] --[[ Line: 334 ]]
    --[[ Upvalues: (copy 1): f_character_copy_accessories_of_attachment_name ]]
    f_character_copy_accessories_of_attachment_name(p72, p73, p74)
end;
return v_u_10;
