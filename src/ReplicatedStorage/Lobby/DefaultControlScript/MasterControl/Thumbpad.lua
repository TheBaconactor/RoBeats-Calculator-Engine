-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:32 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local s_UserInputService_0 = game:GetService("UserInputService")
local s_GuiService_0 = game:GetService("GuiService")
local v_u_1 = require(script.Parent)
local v2 = {}
while not s_Players_0.LocalPlayer do
    wait()
end;
local v_u_3 = nil
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = Vector3.new(0, 0, 0)
local function _(p9, p10, p11, p12, p13, p14) --[[ Name: createArrowLabel ]] --[[ Line: 33 ]]
    local l_ImageLabel_0 = Instance.new("ImageLabel")
    l_ImageLabel_0.Name = p9
    l_ImageLabel_0.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_0.ImageRectOffset = p13
    l_ImageLabel_0.ImageRectSize = p14
    l_ImageLabel_0.BackgroundTransparency = 1
    l_ImageLabel_0.ImageColor3 = Color3.new(0.7450980392156863, 0.7450980392156863, 0.7450980392156863)
    l_ImageLabel_0.Size = p12
    l_ImageLabel_0.Position = p11
    l_ImageLabel_0.Parent = p10
    return l_ImageLabel_0;
end;
v2.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 49 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    v_u_3.Visible = true
end;
v2.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 53 ]]
    --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_5 ]]
    v_u_3.Visible = false
    v_u_5()
end;
v2.Create = function(_, p15) --[[ Name: Create ]] --[[ Line: 58 ]]
    --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_7, (copy 4): v_u_1, (ref 5): v_u_8, (ref 6): v_u_4, (copy 7): s_UserInputService_0, (ref 8): v_u_5, (copy 9): s_GuiService_0 ]]
    if v_u_3 then
        v_u_3:Destroy()
        v_u_3 = nil
        if v_u_6 then
            v_u_6:disconnect()
            v_u_6 = nil
        end;
        if v_u_7 then
            v_u_7:disconnect()
            v_u_7 = nil
        end;
    end;
    local v16 = p15.AbsoluteSize.y <= 500
    local v_u_17 = v16 and 70 or 120
    local v_u_18 = v16 and UDim2.new(0, v_u_17 * 1.25, 1, -v_u_17 - 20) or UDim2.new(0, v_u_17 / 2 - 10, 1, -v_u_17 * 1.75 - 10)
    v_u_3 = Instance.new("Frame")
    v_u_3.Name = "ThumbpadFrame"
    v_u_3.Visible = false
    v_u_3.Active = true
    v_u_3.Size = UDim2.new(0, v_u_17 + 20, 0, v_u_17 + 20)
    v_u_3.Position = v_u_18
    v_u_3.BackgroundTransparency = 1
    local l_ImageLabel_1 = Instance.new("ImageLabel")
    l_ImageLabel_1.Name = "OuterImage"
    l_ImageLabel_1.Image = "rbxasset://textures/ui/TouchControlsSheet.png"
    l_ImageLabel_1.ImageRectOffset = Vector2.new(0, 0)
    l_ImageLabel_1.ImageRectSize = Vector2.new(220, 220)
    l_ImageLabel_1.BackgroundTransparency = 1
    l_ImageLabel_1.Size = UDim2.new(0, v_u_17, 0, v_u_17)
    l_ImageLabel_1.Position = UDim2.new(0, 10, 0, 10)
    l_ImageLabel_1.Parent = v_u_3
    local v_u_19 = v16 and UDim2.new(0, 32, 0, 32) or UDim2.new(0, 64, 0, 64)
    local v_u_20 = UDim2.new(0, v_u_19.X.Offset * 2, 0, v_u_19.Y.Offset * 2)
    local v21 = Vector2.new(110, 110)
    local v_u_22 = v16 and -4 or -9
    local v_u_23 = v16 and -28 or -55
    local v24 = UDim2.new(0.5, -v_u_19.X.Offset / 2, 1, v_u_23)
    local v25 = Vector2.new(8, 8)
    local l_ImageLabel_2 = Instance.new("ImageLabel")
    l_ImageLabel_2.Name = "DownArrow"
    l_ImageLabel_2.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_2.ImageRectOffset = v25
    l_ImageLabel_2.ImageRectSize = v21
    l_ImageLabel_2.BackgroundTransparency = 1
    l_ImageLabel_2.ImageColor3 = Color3.new(0.7450980392156863, 0.7450980392156863, 0.7450980392156863)
    l_ImageLabel_2.Size = v_u_19
    l_ImageLabel_2.Position = v24
    l_ImageLabel_2.Parent = l_ImageLabel_1
    local v26 = UDim2.new(0.5, -v_u_19.X.Offset / 2, 0, v_u_22)
    local v27 = Vector2.new(8, 266)
    local l_ImageLabel_3 = Instance.new("ImageLabel")
    l_ImageLabel_3.Name = "UpArrow"
    l_ImageLabel_3.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_3.ImageRectOffset = v27
    l_ImageLabel_3.ImageRectSize = v21
    l_ImageLabel_3.BackgroundTransparency = 1
    l_ImageLabel_3.ImageColor3 = Color3.new(0.7450980392156863, 0.7450980392156863, 0.7450980392156863)
    l_ImageLabel_3.Size = v_u_19
    l_ImageLabel_3.Position = v26
    l_ImageLabel_3.Parent = l_ImageLabel_1
    local v28 = UDim2.new(0, v_u_22, 0.5, -v_u_19.Y.Offset / 2)
    local v29 = Vector2.new(137, 137)
    local l_ImageLabel_4 = Instance.new("ImageLabel")
    l_ImageLabel_4.Name = "LeftArrow"
    l_ImageLabel_4.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_4.ImageRectOffset = v29
    l_ImageLabel_4.ImageRectSize = v21
    l_ImageLabel_4.BackgroundTransparency = 1
    l_ImageLabel_4.ImageColor3 = Color3.new(0.7450980392156863, 0.7450980392156863, 0.7450980392156863)
    l_ImageLabel_4.Size = v_u_19
    l_ImageLabel_4.Position = v28
    l_ImageLabel_4.Parent = l_ImageLabel_1
    local v_u_30 = l_ImageLabel_4
    local v31 = UDim2.new(1, v_u_23, 0.5, -v_u_19.Y.Offset / 2)
    local v32 = Vector2.new(8, 137)
    local l_ImageLabel_5 = Instance.new("ImageLabel")
    l_ImageLabel_5.Name = "RightArrow"
    l_ImageLabel_5.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_5.ImageRectOffset = v32
    l_ImageLabel_5.ImageRectSize = v21
    l_ImageLabel_5.BackgroundTransparency = 1
    l_ImageLabel_5.ImageColor3 = Color3.new(0.7450980392156863, 0.7450980392156863, 0.7450980392156863)
    l_ImageLabel_5.Size = v_u_19
    l_ImageLabel_5.Position = v31
    l_ImageLabel_5.Parent = l_ImageLabel_1
    local v_u_33 = l_ImageLabel_5
    local function _(p34, p35, p36) --[[ Name: doTween ]] --[[ Line: 106 ]]
        p34:TweenSizeAndPosition(p35, p36, Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
    end;
    local v_u_37 = nil
    local v_u_38 = false
    local v_u_39 = false
    local v_u_40 = false
    local v_u_41 = false
    local function f_doMove(p42) --[[ Name: doMove ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (ref 3): v_u_37, (copy 4): v_u_17, (ref 5): v_u_40, (ref 6): v_u_41, (copy 7): l_ImageLabel_3, (copy 8): v_u_20, (copy 9): v_u_19, (copy 10): v_u_22, (copy 11): l_ImageLabel_2, (copy 12): v_u_23, (ref 13): v_u_38, (ref 14): v_u_39, (copy 15): v_u_33, (copy 16): v_u_30 ]]
        v_u_1:AddToPlayerMovement(-v_u_8)
        v_u_8 = (Vector2.new(p42.x, p42.y) - v_u_37) / (v_u_17 / 2)
        local l_magnitude_0 = v_u_8.magnitude
        if l_magnitude_0 < 0.1 then
            v_u_8 = Vector3.new(0, 0, 0)
        else
            v_u_8 = v_u_8.unit * ((l_magnitude_0 - 0.1) / 0.9)
            if v_u_8.magnitude == 0 then
                v_u_8 = Vector3.new(0, 0, 0)
            else
                v_u_8 = Vector3.new(v_u_8.x, 0, v_u_8.y).unit
            end;
        end;
        v_u_1:AddToPlayerMovement(v_u_8)
        local v43 = v_u_8:Dot(Vector3.new(0, 0, -1))
        local v44 = v_u_8:Dot(Vector3.new(1, 0, 0))
        if v43 > 0.5 then
            if not v_u_40 then
                v_u_40 = true
                v_u_41 = false
                l_ImageLabel_3:TweenSizeAndPosition(v_u_20, UDim2.new(0.5, -v_u_19.X.Offset, 0, v_u_22 - v_u_19.Y.Offset * 1.5), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
                l_ImageLabel_2:TweenSizeAndPosition(v_u_19, UDim2.new(0.5, -v_u_19.X.Offset / 2, 1, v_u_23), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
            end;
        elseif v43 < -0.5 then
            if not v_u_41 then
                v_u_41 = true
                v_u_40 = false
                l_ImageLabel_2:TweenSizeAndPosition(v_u_20, UDim2.new(0.5, -v_u_19.X.Offset, 1, v_u_23 + v_u_19.Y.Offset / 2), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
                l_ImageLabel_3:TweenSizeAndPosition(v_u_19, UDim2.new(0.5, -v_u_19.X.Offset / 2, 0, v_u_22), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
            end;
        else
            v_u_40 = false
            v_u_41 = false
            l_ImageLabel_2:TweenSizeAndPosition(v_u_19, UDim2.new(0.5, -v_u_19.X.Offset / 2, 1, v_u_23), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
            l_ImageLabel_3:TweenSizeAndPosition(v_u_19, UDim2.new(0.5, -v_u_19.X.Offset / 2, 0, v_u_22), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
        end;
        if v44 > 0.5 then
            if not v_u_38 then
                v_u_38 = true
                v_u_39 = false
                v_u_33:TweenSizeAndPosition(v_u_20, UDim2.new(1, v_u_23 + v_u_19.X.Offset / 2, 0.5, -v_u_19.Y.Offset), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
                v_u_30:TweenSizeAndPosition(v_u_19, UDim2.new(0, v_u_22, 0.5, -v_u_19.Y.Offset / 2), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
                return;
            end;
        elseif v44 < -0.5 then
            if not v_u_39 then
                v_u_39 = true
                v_u_38 = false
                v_u_30:TweenSizeAndPosition(v_u_20, UDim2.new(0, v_u_22 - v_u_19.X.Offset * 1.5, 0.5, -v_u_19.Y.Offset), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
                v_u_33:TweenSizeAndPosition(v_u_19, UDim2.new(1, v_u_23, 0.5, -v_u_19.Y.Offset / 2), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
                return;
            end;
        else
            v_u_38 = false
            v_u_39 = false
            v_u_30:TweenSizeAndPosition(v_u_19, UDim2.new(0, v_u_22, 0.5, -v_u_19.Y.Offset / 2), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
            v_u_33:TweenSizeAndPosition(v_u_19, UDim2.new(1, v_u_23, 0.5, -v_u_19.Y.Offset / 2), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
        end;
    end;
    v_u_3.InputBegan:connect(function(p45) --[[ Line: 177 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_3, (ref 3): v_u_37, (copy 4): f_doMove ]]
        if not v_u_4 and p45.UserInputType == Enum.UserInputType.Touch then
            v_u_3.Position = UDim2.new(0, p45.Position.x - v_u_3.AbsoluteSize.x / 2, 0, p45.Position.y - v_u_3.Size.Y.Offset / 2)
            v_u_37 = Vector2.new(v_u_3.AbsolutePosition.x + v_u_3.AbsoluteSize.x / 2, v_u_3.AbsolutePosition.y + v_u_3.AbsoluteSize.y / 2)
            f_doMove(p45.Position)
            v_u_4 = p45
        end;
    end)
    v_u_6 = s_UserInputService_0.TouchMoved:connect(function(p46, _) --[[ Line: 189 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): f_doMove ]]
        if p46 == v_u_4 then
            f_doMove(v_u_4.Position)
        end;
    end)
    v_u_5 = function() --[[ Line: 195 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (ref 3): v_u_3, (copy 4): v_u_18, (ref 5): v_u_4, (ref 6): v_u_40, (ref 7): v_u_41, (ref 8): v_u_39, (ref 9): v_u_38, (copy 10): l_ImageLabel_2, (copy 11): v_u_19, (copy 12): v_u_23, (copy 13): l_ImageLabel_3, (copy 14): v_u_22, (copy 15): v_u_30, (copy 16): v_u_33 ]]
        v_u_1:AddToPlayerMovement(-v_u_8)
        v_u_8 = Vector3.new(0, 0, 0)
        v_u_1:SetIsJumping(false)
        v_u_3.Position = v_u_18
        v_u_4 = nil
        v_u_40 = false
        v_u_41 = false
        v_u_39 = false
        v_u_38 = false
        l_ImageLabel_2:TweenSizeAndPosition(v_u_19, UDim2.new(0.5, -v_u_19.X.Offset / 2, 1, v_u_23), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
        l_ImageLabel_3:TweenSizeAndPosition(v_u_19, UDim2.new(0.5, -v_u_19.X.Offset / 2, 0, v_u_22), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
        v_u_30:TweenSizeAndPosition(v_u_19, UDim2.new(0, v_u_22, 0.5, -v_u_19.Y.Offset / 2), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
        v_u_33:TweenSizeAndPosition(v_u_19, UDim2.new(1, v_u_23, 0.5, -v_u_19.Y.Offset / 2), Enum.EasingDirection.InOut, Enum.EasingStyle.Linear, 0.15, true)
    end
    v_u_7 = s_UserInputService_0.TouchEnded:connect(function(p47) --[[ Line: 209 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5 ]]
        if p47 == v_u_4 then
            v_u_5()
        end;
    end)
    s_GuiService_0.MenuOpened:connect(function() --[[ Line: 215 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5 ]]
        if v_u_4 then
            v_u_5()
        end;
    end)
    v_u_3.Parent = p15
end;
return v2;
