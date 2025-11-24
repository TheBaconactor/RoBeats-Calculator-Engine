-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_2 = require(game.ReplicatedStorage.Shared.LocalWeldAccessories)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_37 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1 ]]
        local v9 = {
            ["requires_apply_appearance_async"] = function(_) --[[ Name: requires_apply_appearance_async ]] --[[ Line: 24 ]]
                return false;
            end,
            ["apply_appearance_async"] = function(_, _, p8) --[[ Name: apply_appearance_async ]] --[[ Line: 25 ]]
                p8()
            end,
            ["is_debug"] = function(_) --[[ Name: is_debug ]] --[[ Line: 44 ]]
                return false;
            end,
            ["is_hair"] = function(_) --[[ Name: is_hair ]] --[[ Line: 48 ]]
                return false;
            end
        }
        v9.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:errf("SPAvatarEquipmentBase must implement get_name")
        end;
        v9.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:errf("SPAvatarEquipmentBase must implement get_avatar_slot")
        end;
        v9.apply_appearance = function(p10, _) --[[ Name: apply_appearance ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:warnf("gear(%s) has not implemented apply_appearance", p10:get_name())
        end;
        v9.get_gear_power = function(p11) --[[ Name: get_gear_power ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:warnf("gear(%s) has not implemented get_gear_power", p11:get_name())
            return 0;
        end;
        v9.get_gear_tier = function(p12) --[[ Name: get_gear_tier ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:warnf("gear(%s) has not implemented get_gear_tier", p12:get_name())
            return 0;
        end;
        v9.get_gear_statmodifierobj = function(p13) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:warnf("gear(%s) has not implemented get_gear_statmodifierobj", p13:get_name())
            return {};
        end;
        v9.get_icon = function(p14) --[[ Name: get_icon ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:warnf("gear(%s) has not implemented get_icon", p14:get_name())
            return "";
        end;
        v9.modify_equip_data_params = function(p15, p16) --[[ Name: modify_equip_data_params ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            if p15:get_avatar_slot() == v_u_1.HAT then
                p16.HasHair = p15:is_hair()
            end;
        end;
        return v9;
    end,
    ["define_as_hair"] = function(_, p17) --[[ Name: define_as_hair ]] --[[ Line: 59 ]]
        p17.is_hair = function(_) --[[ Name: is_hair ]] --[[ Line: 60 ]]
            return true;
        end;
    end,
    ["shirt_base_apply"] = function(_, p18, p19) --[[ Name: shirt_base_apply ]] --[[ Line: 63 ]]
        Instance.new("Shirt", p18).ShirtTemplate = p19
    end,
    ["pants_base_apply"] = function(_, p20, p21) --[[ Name: pants_base_apply ]] --[[ Line: 68 ]]
        Instance.new("Pants", p20).PantsTemplate = p21
    end,
    ["create_accessory_base"] = function(_, _, p22, p23, p24, p25, p26) --[[ Name: create_accessory_base ]] --[[ Line: 72 ]]
        local l_Accessory_0 = Instance.new("Accessory")
        l_Accessory_0.Name = p22
        local l_Part_0 = Instance.new("Part", l_Accessory_0)
        l_Part_0.Name = "Handle"
        l_Part_0.CanCollide = false
        local l_SpecialMesh_0 = Instance.new("SpecialMesh", l_Part_0)
        l_SpecialMesh_0.MeshId = p24
        l_SpecialMesh_0.MeshType = Enum.MeshType.FileMesh
        l_SpecialMesh_0.TextureId = p25
        if p26 ~= nil then
            l_SpecialMesh_0.Scale = p26
        end;
        local l_Attachment_0 = Instance.new("Attachment", l_Part_0)
        l_Attachment_0.Name = p23
        return l_Accessory_0, l_Attachment_0, l_SpecialMesh_0, l_Part_0;
    end,
    ["attach_character_accessory"] = function(_, p27, p28) --[[ Name: attach_character_accessory ]] --[[ Line: 93 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        v_u_2:apply(p27, p28)
    end,
    ["load_accessory_from_modelloaddbasset"] = function(_, p_u_29, p_u_30) --[[ Name: load_accessory_from_modelloaddbasset ]] --[[ Line: 163 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_7, (copy 3): v_u_3, (copy 4): v_u_4 ]]
        v_u_6:singleton():load_model_category(p_u_29, v_u_7.Category.Accessory, function(p31) --[[ Line: 164 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_29, (copy 3): p_u_30, (ref 4): v_u_4 ]]
            if p31 == nil then
                v_u_3:warnf("SPAvatarEquipmentBase:async_load_accessory_from_modelid(%s) load model failed", (tostring(p_u_29)))
                return p_u_30(nil);
            end;
            if p31.ClassName == "Accessory" then
                return p_u_30(p31);
            end;
            local v32 = v_u_4:first_child_of_type(p31, "Accessory")
            if v32 ~= nil then
                return p_u_30(v32);
            end;
            v_u_3:warnf("SPAvatarEquipmentBase:async_load_accessory_from_modelid(%s) model had no accessory", (tostring(p_u_29)))
            return p_u_30(nil);
        end)
    end,
    ["character_has_hair"] = function(_, p_u_33) --[[ Name: character_has_hair ]] --[[ Line: 182 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v_u_34 = false
        pcall(function() --[[ Line: 184 ]]
            --[[ Upvalues: (copy 1): p_u_33, (ref 2): v_u_4, (ref 3): v_u_34 ]]
            for _, v35 in pairs(p_u_33:GetChildren()) do
                if v35.ClassName == "Accessory" then
                    for _, v36 in pairs(v35:GetChildren()) do
                        if v36:IsA("BasePart") and v_u_4:first_child_of_type(v36, "Attachment").Name == "HairAttachment" then
                            v_u_34 = true
                            return;
                        end;
                    end;
                end;
            end;
        end)
        return v_u_34;
    end
}
v_u_37.create_particle_emitter_accessory = function(_, p38, p39, p40, p_u_41) --[[ Name: create_particle_emitter_accessory ]] --[[ Line: 101 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4, (copy 3): v_u_37 ]]
    local function _(p42) --[[ Name: reset_emitter ]] --[[ Line: 103 ]]
        --[[ Upvalues: (copy 1): p_u_41 ]]
        p42.Texture = p_u_41
        p42.LockedToPart = false
        p42.VelocityInheritance = 0
        p42.LightEmission = 0
        p42.LightInfluence = 0
        p42.EmissionDirection = Enum.NormalId.Front
    end;
    local v43 = v_u_5:new()
    v_u_4:fill_list_of_direct_children_of_classname(p38, "Accessory", v43)
    for v44 = 1, v43:count() do
        local v45 = v43:get(v44)
        if v45.Name == "EmitterAccessory" then
            local l_Handle_0 = v45.Handle
            l_Handle_0.Size = Vector3.new(0, 0, 0)
            l_Handle_0.Size = p40
            v_u_37:attach_character_accessory(p38, v45)
            local l_Emitter1_0 = l_Handle_0.Emitter1
            local l_Emitter2_0 = l_Handle_0.Emitter2
            l_Emitter1_0.Texture = p_u_41
            l_Emitter1_0.LockedToPart = false
            l_Emitter1_0.VelocityInheritance = 0
            l_Emitter1_0.LightEmission = 0
            l_Emitter1_0.LightInfluence = 0
            l_Emitter1_0.EmissionDirection = Enum.NormalId.Front
            l_Emitter2_0.Texture = p_u_41
            l_Emitter2_0.LockedToPart = false
            l_Emitter2_0.VelocityInheritance = 0
            l_Emitter2_0.LightEmission = 0
            l_Emitter2_0.LightInfluence = 0
            l_Emitter2_0.EmissionDirection = Enum.NormalId.Front
            l_Emitter2_0.Enabled = false
            return v45, v_u_4:first_child_of_type(l_Handle_0, "Attachment"), l_Emitter1_0, l_Emitter2_0;
        end;
    end;
    local l_Accessory_1 = Instance.new("Accessory")
    l_Accessory_1.Name = "EmitterAccessory"
    local l_Part_1 = Instance.new("Part", l_Accessory_1)
    l_Part_1.Name = "Handle"
    l_Part_1.CanCollide = false
    l_Part_1.Transparency = 1
    l_Part_1.Size = p40
    local l_Attachment_1 = Instance.new("Attachment", l_Part_1)
    l_Attachment_1.Name = p39
    local l_ParticleEmitter_0 = Instance.new("ParticleEmitter")
    l_ParticleEmitter_0.Name = "Emitter1"
    l_ParticleEmitter_0.Parent = l_Part_1
    l_ParticleEmitter_0.Rate = 0
    l_ParticleEmitter_0.Texture = p_u_41
    l_ParticleEmitter_0.LockedToPart = false
    l_ParticleEmitter_0.VelocityInheritance = 0
    l_ParticleEmitter_0.LightEmission = 0
    l_ParticleEmitter_0.LightInfluence = 0
    l_ParticleEmitter_0.EmissionDirection = Enum.NormalId.Front
    local l_ParticleEmitter_1 = Instance.new("ParticleEmitter")
    l_ParticleEmitter_1.Name = "Emitter2"
    l_ParticleEmitter_1.Parent = l_Part_1
    l_ParticleEmitter_1.Rate = 0
    l_ParticleEmitter_1.Texture = p_u_41
    l_ParticleEmitter_1.LockedToPart = false
    l_ParticleEmitter_1.VelocityInheritance = 0
    l_ParticleEmitter_1.LightEmission = 0
    l_ParticleEmitter_1.LightInfluence = 0
    l_ParticleEmitter_1.EmissionDirection = Enum.NormalId.Front
    l_ParticleEmitter_1.Enabled = false
    v_u_37:attach_character_accessory(p38, l_Accessory_1)
    return l_Accessory_1, l_Attachment_1, l_ParticleEmitter_0, l_ParticleEmitter_1;
end;
return v_u_37;
