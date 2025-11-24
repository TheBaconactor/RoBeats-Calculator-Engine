-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:33 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local v_u_1 = require(script.Parent)
local function _(p2) --[[ Name: IsFinite ]] --[[ Line: 7 ]]
    local v3
    if p2 == p2 and p2 ~= (1 / 0) then
        v3 = p2 ~= (-1 / 0)
    else
        v3 = false
    end;
    return v3;
end;
local function _(p4, p5) --[[ Name: findAngleBetweenXZVectors ]] --[[ Line: 13 ]]
    return math.atan2(p5.X * p4.Z - p5.Z * p4.X, p5.X * p4.X + p5.Z * p4.Z);
end;
return function() --[[ Name: CreateAttachCamera ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): s_Players_0 ]]
    local v_u_6 = v_u_1()
    local v_u_7 = tick()
    v_u_6.Update = function(p8) --[[ Name: Update ]] --[[ Line: 21 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (ref 2): v_u_7, (copy 3): v_u_6 ]]
        local v9 = tick()
        local l_CurrentCamera_0 = workspace.CurrentCamera
        local l_LocalPlayer_0 = s_Players_0.LocalPlayer
        if v_u_7 == nil or v9 - v_u_7 > 1 then
            v_u_6:ResetCameraLook()
            p8.LastCameraTransform = nil
        end;
        local v10 = p8:GetSubjectPosition()
        if v10 and (l_LocalPlayer_0 and l_CurrentCamera_0) then
            local v11 = p8:GetCameraZoom()
            local v12 = v11 <= 0 and 0.1 or v11
            local v13 = p8:GetHumanoid()
            if v_u_7 and (v13 and v13.Torso) then
                p8.RotateInput = p8.RotateInput + p8:UpdateGamepad() * math.min(0.1, v9 - v_u_7)
                local l_lookVector_0 = v13.Torso.CFrame.lookVector
                local v14 = p8:GetCameraLook()
                local v15 = math.atan2(v14.X * l_lookVector_0.Z - v14.Z * l_lookVector_0.X, v14.X * l_lookVector_0.X + v14.Z * l_lookVector_0.Z)
                local v16
                if v15 == v15 and v15 ~= (1 / 0) then
                    v16 = v15 ~= (-1 / 0)
                else
                    v16 = false
                end;
                if v16 then
                    p8.RotateInput = Vector2.new(v15, p8.RotateInput.Y)
                end;
            end;
            local v17 = p8:RotateCamera(p8:GetCameraLook(), p8.RotateInput)
            p8.RotateInput = Vector2.new()
            l_CurrentCamera_0.Focus = CFrame.new(v10)
            l_CurrentCamera_0.CoordinateFrame = CFrame.new(l_CurrentCamera_0.Focus.p - v12 * v17, l_CurrentCamera_0.Focus.p)
            p8.LastCameraTransform = l_CurrentCamera_0.CoordinateFrame
        end;
        v_u_7 = v9
    end;
    return v_u_6;
end;
