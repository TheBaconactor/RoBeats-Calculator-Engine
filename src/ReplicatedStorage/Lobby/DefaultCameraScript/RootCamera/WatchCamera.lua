-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:33 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local v_u_1 = require(script.Parent)
return function() --[[ Name: CreateWatchCamera ]] --[[ Line: 5 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): s_Players_0 ]]
    local v_u_2 = v_u_1()
    v_u_2.PanEnabled = false
    local v_u_3 = tick()
    v_u_2.Update = function(p4) --[[ Name: Update ]] --[[ Line: 10 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (ref 2): v_u_3, (copy 3): v_u_2 ]]
        local v5 = tick()
        local l_CurrentCamera_0 = workspace.CurrentCamera
        local l_LocalPlayer_0 = s_Players_0.LocalPlayer
        if v_u_3 == nil or v5 - v_u_3 > 1 then
            v_u_2:ResetCameraLook()
            p4.LastCameraTransform = nil
            p4.LastZoom = nil
        end;
        local v6 = p4:GetSubjectPosition()
        if v6 and (l_LocalPlayer_0 and l_CurrentCamera_0) then
            local v7 = nil
            if p4.LastCameraTransform then
                local v8 = p4:GetHumanoid()
                if v8 and v8.Torso then
                    local v9 = v6 - p4.LastCameraTransform.p
                    v7 = v9.unit
                    if p4.LastZoom and p4.LastZoom == p4:GetCameraZoom() then
                        p4:ZoomCamera(v9.magnitude)
                    end;
                end;
            end;
            local v10 = p4:GetCameraZoom()
            local v11 = v10 <= 0 and 0.1 or v10
            local v12 = p4:RotateVector(v7 or p4:GetCameraLook(), p4.RotateInput)
            p4.RotateInput = Vector2.new()
            local v13 = CFrame.new(v6)
            local v14 = CFrame.new(v13.p - v11 * v12, v13.p)
            l_CurrentCamera_0.Focus = v13
            l_CurrentCamera_0.CoordinateFrame = v14
            p4.LastCameraTransform = v14
            p4.LastZoom = v11
        end;
        v_u_3 = v5
    end;
    return v_u_2;
end;
