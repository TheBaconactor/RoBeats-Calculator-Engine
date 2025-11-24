-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:33 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local v_u_1 = require(script.Parent)
return function() --[[ Name: CreateFixedCamera ]] --[[ Line: 5 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): s_Players_0 ]]
    local v_u_2 = v_u_1()
    local v_u_3 = tick()
    v_u_2.Update = function(p4) --[[ Name: Update ]] --[[ Line: 9 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (ref 2): v_u_3, (copy 3): v_u_2 ]]
        local v5 = tick()
        local l_CurrentCamera_0 = workspace.CurrentCamera
        local l_LocalPlayer_0 = s_Players_0.LocalPlayer
        if v_u_3 == nil or v5 - v_u_3 > 1 then
            v_u_2:ResetCameraLook()
            p4.LastCameraTransform = nil
        end;
        if v_u_3 then
            p4.RotateInput = p4.RotateInput + p4:UpdateGamepad() * math.min(0.1, v5 - v_u_3)
        end;
        if p4:GetSubjectPosition() and (l_LocalPlayer_0 and l_CurrentCamera_0) then
            local v6 = p4:GetCameraZoom()
            local v7 = v6 <= 0 and 0.1 or v6
            local v8 = p4:RotateCamera(p4:GetCameraLook(), p4.RotateInput)
            p4.RotateInput = Vector2.new()
            l_CurrentCamera_0.CoordinateFrame = CFrame.new(l_CurrentCamera_0.Focus.p - v7 * v8, l_CurrentCamera_0.Focus.p)
            p4.LastCameraTransform = l_CurrentCamera_0.CoordinateFrame
        end;
        v_u_3 = v5
    end;
    return v_u_2;
end;
