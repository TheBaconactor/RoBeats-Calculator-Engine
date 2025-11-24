-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local _ = game:GetService("RunService")
local s_UserInputService_0 = game:GetService("UserInputService")
local _ = game:GetService("GamepadService")
pcall(function() --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): s_UserInputService_0 ]]
    local l_VREnabled_0 = s_UserInputService_0.VREnabled
    if l_VREnabled_0 then
        l_VREnabled_0 = s_UserInputService_0.GetUserCFrame
    end;
    return l_VREnabled_0;
end)
local v1 = {}
while not s_Players_0.LocalPlayer do
    wait()
end;
local l_LocalPlayer_0 = s_Players_0.LocalPlayer
local v_u_2 = nil
local l_Move_0 = l_LocalPlayer_0.Move
local v_u_3 = false
local v_u_4 = Vector3.new(0, 0, 0)
local v_u_5 = 0
v1.get_allocid = function(_) --[[ Name: get_allocid ]] --[[ Line: 45 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    return v_u_5;
end;
local v_u_6 = true
v1.GetHumanoid = function(_) --[[ Name: GetHumanoid ]] --[[ Line: 50 ]]
    --[[ Upvalues: (copy 1): l_LocalPlayer_0, (ref 2): v_u_2 ]]
    local v7 = l_LocalPlayer_0
    if v7 then
        v7 = l_LocalPlayer_0.Character
    end;
    if v7 then
        if v_u_2 and v_u_2.Parent == v7 then
            return v_u_2;
        end;
        v_u_2 = nil
        for _, v8 in pairs(v7:GetChildren()) do
            if v8:IsA("Humanoid") then
                v_u_2 = v8
                return v_u_2;
            end;
        end;
    end;
end;
local v_u_9 = 250
local v_u_10 = false
local v_u_11 = 0
v1.set_next_jump_as_boosted = function(_, p12, p13) --[[ Name: set_next_jump_as_boosted ]] --[[ Line: 71 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_9, (ref 3): v_u_11 ]]
    if p12 then
        v_u_10 = true
        v_u_9 = p13
        v_u_11 = 0
    else
        v_u_10 = false
        v_u_11 = 0
    end;
end;
local v_u_14 = false
v1.force_jump = function(_) --[[ Name: force_jump ]] --[[ Line: 83 ]]
    --[[ Upvalues: (ref 1): v_u_14 ]]
    v_u_14 = true
end;
v1.is_force_jump = function(_) --[[ Name: is_force_jump ]] --[[ Line: 87 ]]
    --[[ Upvalues: (ref 1): v_u_14 ]]
    return v_u_14;
end;
v1.Update = function(p15, p16, p17) --[[ Name: Update ]] --[[ Line: 90 ]]
    --[[ Upvalues: (copy 1): l_LocalPlayer_0, (ref 2): v_u_3, (ref 3): v_u_14, (ref 4): v_u_10, (ref 5): v_u_9, (ref 6): v_u_11, (ref 7): v_u_6, (copy 8): l_Move_0, (ref 9): v_u_4 ]]
    local l_CurveUtil_0 = p17.CurveUtil
    if l_LocalPlayer_0 and l_LocalPlayer_0.Character then
        local v18 = p15:GetHumanoid()
        if not v18 then
            return;
        end;
        if v18 and (not v18.PlatformStand and (v_u_3 or v_u_14)) then
            if v_u_10 then
                v18.JumpPower = v_u_9
            else
                v18.JumpPower = 50
            end;
            v18.Jump = true
            v_u_14 = false
        end;
        if v18.JumpPower ~= 50 then
            if v_u_10 then
                v_u_11 = v_u_11 + l_CurveUtil_0:TimescaleToDeltaTime(p16)
                if v_u_11 > 0.15 then
                    v_u_10 = false
                    v18.JumpPower = 50
                end;
            else
                v18.JumpPower = 50
            end;
        end;
        if v_u_6 == true then
            l_Move_0(l_LocalPlayer_0, v_u_4, true)
        end;
    end;
    return v_u_4;
end;
v1.get_move_vector = function(_) --[[ Name: get_move_vector ]] --[[ Line: 148 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    return v_u_4;
end;
v1.is_jumping = function(_) --[[ Name: is_jumping ]] --[[ Line: 149 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    return v_u_3;
end;
v1.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 151 ]]
    --[[ Upvalues: (ref 1): v_u_3, (copy 2): l_Move_0, (copy 3): l_LocalPlayer_0, (ref 4): v_u_6 ]]
    v_u_3 = false
    l_Move_0(l_LocalPlayer_0, Vector3.new(), true)
    v_u_6 = false
end;
v1.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 164 ]]
    --[[ Upvalues: (ref 1): v_u_6 ]]
    v_u_6 = true
end;
v1.AddToPlayerMovement = function(_, p19) --[[ Name: AddToPlayerMovement ]] --[[ Line: 168 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    v_u_4 = Vector3.new(v_u_4.X + p19.X, v_u_4.Y + p19.Y, v_u_4.Z + p19.Z)
end;
v1.GetMoveVector = function(_) --[[ Name: GetMoveVector ]] --[[ Line: 176 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    return v_u_4;
end;
v1.SetIsJumping = function(_, p20) --[[ Name: SetIsJumping ]] --[[ Line: 180 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    v_u_3 = p20
end;
v1.DoJump = function(p21) --[[ Name: DoJump ]] --[[ Line: 184 ]]
    local v22 = p21:GetHumanoid()
    if v22 then
        v22.Jump = true
    end;
end;
return v1;
