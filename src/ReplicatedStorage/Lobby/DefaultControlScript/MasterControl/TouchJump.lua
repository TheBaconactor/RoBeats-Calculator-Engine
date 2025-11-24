-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:32 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local s_GuiService_0 = game:GetService("GuiService")
local _, _ = pcall(function() --[[ Line: 11 ]]
    return UserSettings():IsUserFeatureEnabled("UserJumpButtonPositionChange");
end)
local v_u_1 = require(script.Parent)
local v_u_2 = {}
while not s_Players_0.LocalPlayer do
    wait()
end;
local l_LocalPlayer_0 = s_Players_0.LocalPlayer
local v_u_3 = v_u_1:GetHumanoid()
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = false
local v_u_10 = 0
local function _() --[[ Name: updateEnabled ]] --[[ Line: 39 ]]
    --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_2 ]]
    v_u_2:Disable()
end;
local function f_humanoidChanged(p11) --[[ Name: humanoidChanged ]] --[[ Line: 47 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_3, (ref 3): v_u_8 ]]
    if p11 == "JumpPower" then
        v_u_10 = v_u_3.JumpPower
    elseif p11 == "Parent" and not v_u_3.Parent then
        v_u_8:disconnect()
    end;
end;
local function f_humandoidStateEnabledChanged(_, _) end;
local function _() --[[ Name: disableButton ]] --[[ Line: 65 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5 ]]
    if v_u_4 then
        v_u_4.Visible = false
    end;
    if v_u_5 then
        v_u_5()
    end;
end;
local function _() --[[ Name: enableButton ]] --[[ Line: 74 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_3, (ref 3): v_u_9 ]]
    if v_u_4 and (v_u_3 and (v_u_9 and v_u_3.JumpPower > 0)) then
        v_u_4.Visible = true
    end;
end;
local function f_characterAdded(p12) --[[ Name: characterAdded ]] --[[ Line: 82 ]]
    --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_3, (copy 3): v_u_1, (copy 4): f_humanoidChanged, (ref 5): v_u_7, (copy 6): f_humandoidStateEnabledChanged, (ref 7): v_u_10, (copy 8): v_u_2 ]]
    if v_u_8 then
        v_u_8:disconnect()
    end;
    v_u_3 = nil
    repeat
        v_u_3 = v_u_1:GetHumanoid()
        wait()
    until v_u_3 and v_u_3.Parent == p12;
    v_u_8 = v_u_3.Changed:connect(f_humanoidChanged)
    v_u_7 = v_u_3.StateEnabledChanged:connect(f_humandoidStateEnabledChanged)
    v_u_10 = v_u_3.JumpPower
    v_u_2:Disable()
end;
local function _() --[[ Name: setupCharacterAddedFunction ]] --[[ Line: 99 ]]
    --[[ Upvalues: (ref 1): v_u_6, (copy 2): l_LocalPlayer_0, (copy 3): f_characterAdded ]]
    v_u_6 = l_LocalPlayer_0.CharacterAdded:connect(f_characterAdded)
    if l_LocalPlayer_0.Character then
        f_characterAdded(l_LocalPlayer_0.Character)
    end;
end;
local v_u_13 = false
v_u_2.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 108 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_13, (ref 3): v_u_4, (ref 4): v_u_3 ]]
    v_u_9 = true
    v_u_13 = false
    if v_u_4 and (v_u_3 and (v_u_9 and v_u_3.JumpPower > 0)) then
        v_u_4.Visible = true
    end;
end;
v_u_2.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 114 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_13, (ref 3): v_u_4, (ref 4): v_u_5 ]]
    v_u_9 = false
    v_u_13 = false
    if v_u_4 then
        v_u_4.Visible = false
    end;
    if v_u_5 then
        v_u_5()
    end;
end;
v_u_2.Create = function(_, p14) --[[ Name: Create ]] --[[ Line: 120 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_13, (ref 3): v_u_9, (copy 4): v_u_1, (ref 5): v_u_5, (copy 6): s_GuiService_0, (ref 7): v_u_6, (copy 8): l_LocalPlayer_0, (copy 9): f_characterAdded ]]
    if v_u_4 then
        v_u_4:Destroy()
        v_u_4 = nil
    end;
    local v15 = p14.AbsoluteSize.y <= 500
    local v16 = v15 and 70 or 120
    v_u_4 = Instance.new("ImageButton")
    v_u_4.Name = "JumpButton"
    v_u_4.Visible = false
    v_u_4.BackgroundTransparency = 1
    v_u_4.Image = "rbxasset://textures/ui/TouchControlsSheet.png"
    v_u_4.ImageRectOffset = Vector2.new(176, 222)
    v_u_4.ImageRectSize = Vector2.new(174, 174)
    v_u_4.Size = UDim2.new(0, v16, 0, v16)
    if v15 then
        v_u_4.Position = UDim2.new(1, -(v16 * 1.5 - 10), 0.5, -v16 * 0.5)
    else
        v_u_4.Position = UDim2.new(1, -(v16 * 1.5 - 10), 0.5, -v16 * 0.5)
    end;
    local v_u_17 = nil
    v_u_4.InputBegan:connect(function(p18) --[[ Line: 154 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_13, (ref 3): v_u_9, (ref 4): v_u_4, (ref 5): v_u_1 ]]
        if v_u_17 or p18.UserInputType ~= Enum.UserInputType.Touch then
            return;
        else
            if p18.UserInputState == Enum.UserInputState.Begin then
                v_u_13 = v_u_9
            end;
            if v_u_13 == true then
                v_u_17 = p18
                v_u_4.ImageRectOffset = Vector2.new(0, 222)
                v_u_1:SetIsJumping(true)
            end;
        end;
    end)
    v_u_5 = function() --[[ Line: 172 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_4, (ref 4): v_u_13 ]]
        v_u_17 = nil
        v_u_1:SetIsJumping(false)
        v_u_4.ImageRectOffset = Vector2.new(176, 222)
        v_u_13 = false
    end
    v_u_4.InputEnded:connect(function(p19) --[[ Line: 179 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_5 ]]
        if p19 == v_u_17 then
            v_u_5()
        end;
    end)
    s_GuiService_0.MenuOpened:connect(function() --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_5 ]]
        if v_u_17 then
            v_u_5()
        end;
    end)
    if not v_u_6 then
        v_u_6 = l_LocalPlayer_0.CharacterAdded:connect(f_characterAdded)
        if l_LocalPlayer_0.Character then
            f_characterAdded(l_LocalPlayer_0.Character)
        end;
    end;
    v_u_4.Parent = p14
end;
return v_u_2;
