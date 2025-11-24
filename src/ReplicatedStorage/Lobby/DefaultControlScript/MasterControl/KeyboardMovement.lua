-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:32 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local s_UserInputService_0 = game:GetService("UserInputService")
local s_ContextActionService_0 = game:GetService("ContextActionService")
local _ = game:GetService("StarterPlayer")
local v1 = {}
local v_u_2 = 0
v1.get_allocid = function(_) --[[ Name: get_allocid ]] --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): v_u_2 ]]
    return v_u_2;
end;
while not s_Players_0.LocalPlayer do
    wait()
end;
local l_LocalPlayer_0 = s_Players_0.LocalPlayer
local v_u_3 = nil
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = require(script.Parent)
local v_u_9 = Vector3.new(0, 0, 0)
local function f_getHumanoid() --[[ Name: getHumanoid ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): l_LocalPlayer_0, (ref 2): v_u_3 ]]
    local v10 = l_LocalPlayer_0
    if v10 then
        v10 = l_LocalPlayer_0.Character
    end;
    if v10 then
        if v_u_3 and v_u_3.Parent == v10 then
            return v_u_3;
        end;
        v_u_3 = nil
        for _, v11 in pairs(v10:GetChildren()) do
            if v11:IsA("Humanoid") then
                v_u_3 = v11
                return v_u_3;
            end;
        end;
    end;
end;
v1.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 62 ]]
    --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_9, (copy 3): s_ContextActionService_0, (copy 4): f_getHumanoid, (ref 5): v_u_4, (copy 6): s_UserInputService_0, (ref 7): v_u_5, (ref 8): v_u_6, (ref 9): v_u_7 ]]
    local v_u_12 = 0
    local v_u_13 = 0
    local v_u_14 = 0
    local v_u_15 = 0
    local function _(p16) --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_14, (ref 4): v_u_15, (ref 5): v_u_12, (ref 6): v_u_13 ]]
        if p16 == Enum.UserInputState.Cancel then
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(0, 0, 0)
        else
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(v_u_14 + v_u_15, 0, v_u_12 + v_u_13)
            v_u_8:AddToPlayerMovement(v_u_9)
        end;
    end;
    local function v18(_, p17, _) --[[ Line: 88 ]]
        --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_12 ]]
        if p17 == Enum.UserInputState.Begin then
            v_u_13 = 1
        elseif p17 == Enum.UserInputState.End then
            v_u_13 = 0
        end;
        if p17 == Enum.UserInputState.Cancel then
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(0, 0, 0)
        else
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(v_u_14 + v_u_15, 0, v_u_12 + v_u_13)
            v_u_8:AddToPlayerMovement(v_u_9)
        end;
    end;
    local function v20(_, p19, _) --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_15, (ref 5): v_u_12, (ref 6): v_u_13 ]]
        if p19 == Enum.UserInputState.Begin then
            v_u_14 = -1
        elseif p19 == Enum.UserInputState.End then
            v_u_14 = 0
        end;
        if p19 == Enum.UserInputState.Cancel then
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(0, 0, 0)
        else
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(v_u_14 + v_u_15, 0, v_u_12 + v_u_13)
            v_u_8:AddToPlayerMovement(v_u_9)
        end;
    end;
    local function v22(_, p21, _) --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_14, (ref 5): v_u_12, (ref 6): v_u_13 ]]
        if p21 == Enum.UserInputState.Begin then
            v_u_15 = 1
        elseif p21 == Enum.UserInputState.End then
            v_u_15 = 0
        end;
        if p21 == Enum.UserInputState.Cancel then
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(0, 0, 0)
        else
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(v_u_14 + v_u_15, 0, v_u_12 + v_u_13)
            v_u_8:AddToPlayerMovement(v_u_9)
        end;
    end;
    local function v24(_, p23, _) --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        v_u_8:SetIsJumping(p23 == Enum.UserInputState.Begin)
    end;
    s_ContextActionService_0:BindActionToInputTypes("forwardMovement", function(_, p25, _) --[[ Line: 79 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_13 ]]
        if p25 == Enum.UserInputState.Begin then
            v_u_12 = -1
        elseif p25 == Enum.UserInputState.End then
            v_u_12 = 0
        end;
        if p25 == Enum.UserInputState.Cancel then
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(0, 0, 0)
        else
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(v_u_14 + v_u_15, 0, v_u_12 + v_u_13)
            v_u_8:AddToPlayerMovement(v_u_9)
        end;
    end, false, Enum.PlayerActions.CharacterForward)
    s_ContextActionService_0:BindActionToInputTypes("backwardMovement", v18, false, Enum.PlayerActions.CharacterBackward)
    s_ContextActionService_0:BindActionToInputTypes("leftMovement", v20, false, Enum.PlayerActions.CharacterLeft)
    s_ContextActionService_0:BindActionToInputTypes("rightMovement", v22, false, Enum.PlayerActions.CharacterRight)
    s_ContextActionService_0:BindActionToInputTypes("jumpAction", v24, false, Enum.PlayerActions.CharacterJump)
    local function f_onFocusReleased() --[[ Name: onFocusReleased ]] --[[ Line: 131 ]]
        --[[ Upvalues: (ref 1): f_getHumanoid, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_12, (ref 5): v_u_13, (ref 6): v_u_14, (ref 7): v_u_15 ]]
        if f_getHumanoid() then
            v_u_8:AddToPlayerMovement(-v_u_9)
            v_u_9 = Vector3.new(0, 0, 0)
            v_u_12 = 0
            v_u_13 = 0
            v_u_14 = 0
            v_u_15 = 0
            v_u_8:SetIsJumping(false)
        end;
    end;
    local function f_onTextFocusGained(_) --[[ Name: onTextFocusGained ]] --[[ Line: 141 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        v_u_8:SetIsJumping(false)
    end;
    v_u_4 = s_UserInputService_0.InputBegan:connect(function(p26, p27) --[[ Line: 145 ]]
        --[[ Upvalues: (ref 1): f_getHumanoid, (ref 2): v_u_8 ]]
        if p26.KeyCode == Enum.KeyCode.Backspace and not p27 then
            local v28 = f_getHumanoid()
            if v28 and (v28.Sit or v28.PlatformStand) then
                v_u_8:DoJump()
            end;
        end;
    end)
    v_u_5 = s_UserInputService_0.TextBoxFocusReleased:connect(f_onFocusReleased)
    v_u_6 = s_UserInputService_0.TextBoxFocused:connect(f_onTextFocusGained)
    v_u_7 = s_UserInputService_0.WindowFocused:connect(f_onFocusReleased)
end;
v1.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 160 ]]
    --[[ Upvalues: (copy 1): s_ContextActionService_0, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_6, (ref 5): v_u_7, (copy 6): v_u_8, (ref 7): v_u_9 ]]
    s_ContextActionService_0:UnbindAction("forwardMovement")
    s_ContextActionService_0:UnbindAction("backwardMovement")
    s_ContextActionService_0:UnbindAction("leftMovement")
    s_ContextActionService_0:UnbindAction("rightMovement")
    s_ContextActionService_0:UnbindAction("jumpAction")
    if v_u_4 then
        v_u_4:disconnect()
        v_u_4 = nil
    end;
    if v_u_5 then
        v_u_5:disconnect()
        v_u_5 = nil
    end;
    if v_u_6 then
        v_u_6:disconnect()
        v_u_6 = nil
    end;
    if v_u_7 then
        v_u_7:disconnect()
        v_u_7 = nil
    end;
    v_u_8:AddToPlayerMovement(-v_u_9)
    v_u_9 = Vector3.new(0, 0, 0)
    v_u_8:SetIsJumping(false)
end;
return v1;
