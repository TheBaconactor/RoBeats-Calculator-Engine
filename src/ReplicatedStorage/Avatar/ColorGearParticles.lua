-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
return {
    ["attach_color_particle"] = function(_, p3, p4) --[[ Name: attach_color_particle ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        if p3 == v_u_1.Blue then
            local _, _, v5, v6 = v_u_2:create_particle_emitter_accessory(p4, "BodyBackAttachment", Vector3.new(2, 6, 0.05), "http://www.roblox.com/asset/?id=5033315145")
            v5.EmissionDirection = Enum.NormalId.Back
            v5.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 115, 117)), ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 115, 117)) })
            v5.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.2), NumberSequenceKeypoint.new(1, 0.2) })
            v5.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.25), NumberSequenceKeypoint.new(1, 1) })
            v5.ZOffset = 0
            v5.Acceleration = Vector3.new(0, 0, -0.05)
            v5.Drag = 0.5
            v5.Lifetime = NumberRange.new(1.2, 1.2)
            v5.Rate = v5.Rate + 3
            v5.Rotation = NumberRange.new(-45, 45)
            v5.RotSpeed = NumberRange.new(140, 140)
            v5.Speed = NumberRange.new(1, 2)
            v5.SpreadAngle = Vector2.new(2, 0)
            v5.Enabled = true
            v6.Enabled = false
            return;
        elseif p3 == v_u_1.Green then
            local _, _, v7, v8 = v_u_2:create_particle_emitter_accessory(p4, "BodyBackAttachment", Vector3.new(6, 6, 4), "http://www.roblox.com/asset/?id=5033262232")
            v8.Texture = "http://www.roblox.com/asset/?id=5033233284"
            v7.EmissionDirection = Enum.NormalId.Back
            v8.EmissionDirection = v7.EmissionDirection
            v7.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)), ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 255, 255)) })
            v8.Color = v7.Color
            v7.Size = NumberSequence.new({
                NumberSequenceKeypoint.new(0, 0),
                NumberSequenceKeypoint.new(0.0429, 0.25),
                NumberSequenceKeypoint.new(0.0777, 0.625),
                NumberSequenceKeypoint.new(0.129, 0.25),
                NumberSequenceKeypoint.new(1, 0)
            })
            v8.Size = v7.Size
            v7.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.5), NumberSequenceKeypoint.new(1, 1) })
            v8.Transparency = v7.Transparency
            v7.ZOffset = 0
            v8.ZOffset = v7.ZOffset
            v7.Acceleration = Vector3.new(0, 0, -0.05)
            v8.Acceleration = v7.Acceleration
            v7.Drag = 0.5
            v8.Drag = v7.Drag
            v7.Lifetime = NumberRange.new(2, 5)
            v8.Lifetime = v7.Lifetime
            v7.Rate = v7.Rate + 1
            v8.Rate = v7.Rate
            v7.Rotation = NumberRange.new(-45, 45)
            v8.Rotation = v7.Rotation
            v7.RotSpeed = NumberRange.new(-5, 5)
            v8.RotSpeed = v7.RotSpeed
            v7.Speed = NumberRange.new(1, 2)
            v8.Speed = v7.Speed
            v7.SpreadAngle = Vector2.new(2, 0)
            v8.SpreadAngle = v7.SpreadAngle
            v7.Enabled = true
            v8.Enabled = true
            return;
        elseif p3 == v_u_1.Purple then
            local _, _, v9, v10 = v_u_2:create_particle_emitter_accessory(p4, "BodyBackAttachment", Vector3.new(5, 0.5, 1), "http://www.roblox.com/asset/?id=5033396378")
            v9.EmissionDirection = Enum.NormalId.Bottom
            v9.LightEmission = 1
            v9.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)), ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 0, 0)) })
            v9.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.5), NumberSequenceKeypoint.new(1, 0.5) })
            v9.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.0875), NumberSequenceKeypoint.new(0.666, 0.181), NumberSequenceKeypoint.new(1, 0.819) })
            v9.ZOffset = 0
            v9.Acceleration = Vector3.new(0, 0, 0)
            v9.Drag = 0
            v9.Lifetime = NumberRange.new(0.17, 0.19)
            v9.Rate = v9.Rate + 3
            v9.Rotation = NumberRange.new(0, 0)
            v9.RotSpeed = NumberRange.new(0, 0)
            v9.Speed = NumberRange.new(16, 18)
            v9.SpreadAngle = Vector2.new(0, 0)
            v9.Enabled = true
            v10.Texture = "http://www.roblox.com/asset/?id=5033371628"
            v10.EmissionDirection = Enum.NormalId.Bottom
            v10.LightEmission = 1
            v10.Color = v9.Color
            v10.Size = v9.Size
            v10.Transparency = v9.Transparency
            v10.ZOffset = 0
            v10.Acceleration = Vector3.new(0, 0, 0)
            v10.Drag = 0
            v10.Lifetime = NumberRange.new(0.3, 0.4)
            v10.Rate = v10.Rate + 1
            v10.Rotation = NumberRange.new(0, 0)
            v10.RotSpeed = NumberRange.new(0, 0)
            v10.Speed = NumberRange.new(1, 1.2)
            v10.SpreadAngle = Vector2.new(0, 0)
            v10.Enabled = true
            return;
        elseif p3 == v_u_1.Red then
            local _, _, v11, v12 = v_u_2:create_particle_emitter_accessory(p4, "BodyBackAttachment", Vector3.new(3.886, 6.368, 5), "rbxassetid://5512745160")
            v11.EmissionDirection = Enum.NormalId.Back
            v11.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 115, 117)), ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 115, 117)) })
            v11.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.2), NumberSequenceKeypoint.new(0.181, 0.75), NumberSequenceKeypoint.new(1, 0.375) })
            v11.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.25), NumberSequenceKeypoint.new(1, 1) })
            v11.ZOffset = 0
            v11.Acceleration = Vector3.new(0, -1, 0)
            v11.Drag = 0.25
            v11.Lifetime = NumberRange.new(0.5, 1)
            v11.Rate = v11.Rate + 3
            v11.Rotation = NumberRange.new(-45, -45)
            v11.RotSpeed = NumberRange.new(-5, 5)
            v11.Speed = NumberRange.new(0, 0)
            v11.SpreadAngle = Vector2.new(0, 0)
            v11.Enabled = true
            v12.Enabled = false
        elseif p3 == v_u_1.Orange then
            local _, _, v13, v14 = v_u_2:create_particle_emitter_accessory(p4, "BodyBackAttachment", Vector3.new(4, 6, 2), "http://www.roblox.com/asset/?id=5033352242")
            v13.EmissionDirection = Enum.NormalId.Back
            v13.LockedToPart = true
            v13.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)), ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 0, 0)) })
            v13.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.5), NumberSequenceKeypoint.new(0.1, 0.7), NumberSequenceKeypoint.new(1, 0.5) })
            v13.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.25), NumberSequenceKeypoint.new(1, 1) })
            v13.ZOffset = 0
            v13.Acceleration = Vector3.new(0, 0, 0)
            v13.Drag = 0
            v13.Lifetime = NumberRange.new(0.4, 0.4)
            v13.Rate = v13.Rate + 3
            v13.Rotation = NumberRange.new(-45, 45)
            v13.RotSpeed = NumberRange.new(-5, 5)
            v13.Speed = NumberRange.new(0, 0.5)
            v13.SpreadAngle = Vector2.new(-10, 10)
            v13.Enabled = true
            v14.Enabled = false
        end;
    end
};
