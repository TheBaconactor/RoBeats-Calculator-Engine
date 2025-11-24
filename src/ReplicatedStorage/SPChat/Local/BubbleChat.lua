-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:53 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local _ = game:GetService("ReplicatedStorage")
local s_TextService_0 = game:GetService("TextService")
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local function f_SetupBubbleChat() --[[ Name: SetupBubbleChat ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): s_Players_0, (copy 2): s_TextService_0, (copy 3): v_u_1 ]]
    local l_LocalPlayer_0 = s_Players_0.LocalPlayer
    while l_LocalPlayer_0 == nil do
        s_Players_0.ChildAdded:wait()
        l_LocalPlayer_0 = s_Players_0.LocalPlayer
    end;
    local v2 = l_LocalPlayer_0:WaitForChild("PlayerGui")
    local l_SourceSans_0 = Enum.Font.SourceSans
    local l_Size24_0 = Enum.FontSize.Size24
    local v_u_3 = {
        ["WHITE"] = "dub",
        ["BLUE"] = "blu",
        ["GREEN"] = "gre",
        ["RED"] = "red"
    }
    local l_ScreenGui_0 = Instance.new("ScreenGui")
    l_ScreenGui_0.Name = "BubbleChat"
    l_ScreenGui_0.ResetOnSpawn = false
    l_ScreenGui_0.Parent = v2
    local function _(p4, p5, p6) --[[ Name: lerpLength ]] --[[ Line: 62 ]]
        return p5 + (p6 - p5) * math.min(string.len(p4) / 75, 1);
    end;
    local function f_createFifo() --[[ Name: createFifo ]] --[[ Line: 66 ]]
        local v_u_7 = {
            ["data"] = {},
            ["Emptied"] = l_BindableEvent_0.Event
        }
        local l_BindableEvent_0 = Instance.new("BindableEvent")
        v_u_7.Size = function(_) --[[ Name: Size ]] --[[ Line: 73 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return #v_u_7.data;
        end;
        v_u_7.Empty = function(_) --[[ Name: Empty ]] --[[ Line: 77 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7:Size() <= 0;
        end;
        v_u_7.PopFront = function(_) --[[ Name: PopFront ]] --[[ Line: 81 ]]
            --[[ Upvalues: (copy 1): v_u_7, (copy 2): l_BindableEvent_0 ]]
            table.remove(v_u_7.data, 1)
            if v_u_7:Empty() then
                l_BindableEvent_0:Fire()
            end;
        end;
        v_u_7.Front = function(_) --[[ Name: Front ]] --[[ Line: 86 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7.data[1];
        end;
        v_u_7.Get = function(_, p8) --[[ Name: Get ]] --[[ Line: 90 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7.data[p8];
        end;
        v_u_7.PushBack = function(_, p9) --[[ Name: PushBack ]] --[[ Line: 94 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            table.insert(v_u_7.data, p9)
        end;
        v_u_7.GetData = function(_) --[[ Name: GetData ]] --[[ Line: 98 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7.data;
        end;
        return v_u_7;
    end;
    local function _() --[[ Name: createCharacterChats ]] --[[ Line: 105 ]]
        --[[ Upvalues: (copy 1): f_createFifo ]]
        return {
            ["Fifo"] = f_createFifo(),
            ["BillboardGui"] = nil
        };
    end;
    local function f_createChatLine(p10, p11, p12) --[[ Name: createChatLine ]] --[[ Line: 153 ]]
        local v15 = {
            ["ComputeBubbleLifetime"] = function(_, p13, p14) --[[ Name: ComputeBubbleLifetime ]] --[[ Line: 156 ]]
                if p14 then
                    return 8 + 7 * math.min(string.len(p13) / 75, 1);
                else
                    return 12 + 8 * math.min(string.len(p13) / 75, 1);
                end;
            end,
            ["Origin"] = nil,
            ["RenderBubble"] = nil,
            ["Message"] = p10,
            ["BubbleDieDelay"] = v15:ComputeBubbleLifetime(p10, p12),
            ["BubbleColor"] = p11,
            ["IsLocalPlayer"] = p12
        }
        return v15;
    end;
    local function _(p16, p17, p18) --[[ Name: createPlayerChatLine ]] --[[ Line: 174 ]]
        --[[ Upvalues: (copy 1): f_createChatLine, (copy 2): v_u_3 ]]
        local v19 = f_createChatLine(p17, v_u_3.WHITE, p18)
        if p16 then
            v19.User = p16.Name
            v19.Origin = p16.Character
        end;
        return v19;
    end;
    local function _(p20, p21, p22, p23) --[[ Name: createGameChatLine ]] --[[ Line: 185 ]]
        --[[ Upvalues: (copy 1): f_createChatLine ]]
        local v24 = f_createChatLine(p21, p23, p22)
        v24.Origin = p20
        return v24;
    end;
    local function f_createChatBubbleMain(p25, p26) --[[ Name: createChatBubbleMain ]] --[[ Line: 192 ]]
        local l_ImageLabel_0 = Instance.new("ImageLabel")
        l_ImageLabel_0.Name = "ChatBubble"
        l_ImageLabel_0.ScaleType = Enum.ScaleType.Slice
        l_ImageLabel_0.SliceCenter = p26
        l_ImageLabel_0.Image = "rbxasset://textures/" .. tostring(p25) .. ".png"
        l_ImageLabel_0.BackgroundTransparency = 1
        l_ImageLabel_0.BorderSizePixel = 0
        l_ImageLabel_0.Size = UDim2.new(1, 0, 1, 0)
        l_ImageLabel_0.Position = UDim2.new(0, 0, 0, 0)
        return l_ImageLabel_0;
    end;
    local function _(p27, p28) --[[ Name: createChatBubbleTail ]] --[[ Line: 206 ]]
        local l_ImageLabel_1 = Instance.new("ImageLabel")
        l_ImageLabel_1.Name = "ChatBubbleTail"
        l_ImageLabel_1.Image = "rbxasset://textures/ui/dialog_tail.png"
        l_ImageLabel_1.BackgroundTransparency = 1
        l_ImageLabel_1.BorderSizePixel = 0
        l_ImageLabel_1.Position = p27
        l_ImageLabel_1.Size = p28
        return l_ImageLabel_1;
    end;
    local function _(p29, p30, p31, p32) --[[ Name: createChatBubbleWithTail ]] --[[ Line: 218 ]]
        --[[ Upvalues: (copy 1): f_createChatBubbleMain ]]
        local v33 = f_createChatBubbleMain(p29, p32)
        local l_ImageLabel_2 = Instance.new("ImageLabel")
        l_ImageLabel_2.Name = "ChatBubbleTail"
        l_ImageLabel_2.Image = "rbxasset://textures/ui/dialog_tail.png"
        l_ImageLabel_2.BackgroundTransparency = 1
        l_ImageLabel_2.BorderSizePixel = 0
        l_ImageLabel_2.Position = p30
        l_ImageLabel_2.Size = p31
        l_ImageLabel_2.Parent = v33
        return v33;
    end;
    local function f_createScaledChatBubbleWithTail(p34, p35, p36, p37) --[[ Name: createScaledChatBubbleWithTail ]] --[[ Line: 227 ]]
        --[[ Upvalues: (copy 1): f_createChatBubbleMain ]]
        local v38 = f_createChatBubbleMain(p34, p37)
        local l_Frame_0 = Instance.new("Frame")
        l_Frame_0.Name = "ChatBubbleTailFrame"
        l_Frame_0.BackgroundTransparency = 1
        l_Frame_0.SizeConstraint = Enum.SizeConstraint.RelativeXX
        l_Frame_0.Position = UDim2.new(0.5, 0, 1, 0)
        l_Frame_0.Size = UDim2.new(p35, 0, p35, 0)
        l_Frame_0.Parent = v38
        local v39 = UDim2.new(1, 0, 0.5, 0)
        local l_ImageLabel_3 = Instance.new("ImageLabel")
        l_ImageLabel_3.Name = "ChatBubbleTail"
        l_ImageLabel_3.Image = "rbxasset://textures/ui/dialog_tail.png"
        l_ImageLabel_3.BackgroundTransparency = 1
        l_ImageLabel_3.BorderSizePixel = 0
        l_ImageLabel_3.Position = p36
        l_ImageLabel_3.Size = v39
        l_ImageLabel_3.Parent = l_Frame_0
        return v38;
    end;
    local function _(p40, p41, p42) --[[ Name: createChatImposter ]] --[[ Line: 244 ]]
        local l_ImageLabel_4 = Instance.new("ImageLabel")
        l_ImageLabel_4.Name = "DialogPlaceholder"
        l_ImageLabel_4.Image = "rbxasset://textures/" .. tostring(p40) .. ".png"
        l_ImageLabel_4.BackgroundTransparency = 1
        l_ImageLabel_4.BorderSizePixel = 0
        l_ImageLabel_4.Position = UDim2.new(0, 0, -1.25, 0)
        l_ImageLabel_4.Size = UDim2.new(1, 0, 1, 0)
        local l_ImageLabel_5 = Instance.new("ImageLabel")
        l_ImageLabel_5.Name = "DotDotDot"
        l_ImageLabel_5.Image = "rbxasset://textures/" .. tostring(p41) .. ".png"
        l_ImageLabel_5.BackgroundTransparency = 1
        l_ImageLabel_5.BorderSizePixel = 0
        l_ImageLabel_5.Position = UDim2.new(0.001, 0, p42, 0)
        l_ImageLabel_5.Size = UDim2.new(1, 0, 0.7, 0)
        l_ImageLabel_5.Parent = l_ImageLabel_4
        return l_ImageLabel_4;
    end;
    local v_u_59 = {
        ["ChatBubble"] = {},
        ["ChatBubbleWithTail"] = {},
        ["ScalingChatBubbleWithTail"] = {},
        ["CharacterSortedMsg"] = (function() --[[ Name: createMap ]] --[[ Line: 114 ]]
            --[[ Upvalues: (copy 1): f_createFifo ]]
            local v_u_43 = {
                ["data"] = {}
            }
            local v_u_44 = 0
            v_u_43.Size = function(_) --[[ Name: Size ]] --[[ Line: 119 ]]
                --[[ Upvalues: (ref 1): v_u_44 ]]
                return v_u_44;
            end;
            v_u_43.Erase = function(_, p45) --[[ Name: Erase ]] --[[ Line: 123 ]]
                --[[ Upvalues: (copy 1): v_u_43, (ref 2): v_u_44 ]]
                if v_u_43.data[p45] then
                    v_u_44 = v_u_44 - 1
                end;
                v_u_43.data[p45] = nil
            end;
            v_u_43.Set = function(_, p46, p47) --[[ Name: Set ]] --[[ Line: 128 ]]
                --[[ Upvalues: (copy 1): v_u_43, (ref 2): v_u_44 ]]
                v_u_43.data[p46] = p47
                if p47 then
                    v_u_44 = v_u_44 + 1
                end;
            end;
            v_u_43.Get = function(_, p_u_48) --[[ Name: Get ]] --[[ Line: 133 ]]
                --[[ Upvalues: (copy 1): v_u_43, (ref 2): f_createFifo ]]
                if p_u_48 then
                    if not v_u_43.data[p_u_48] then
                        v_u_43.data[p_u_48] = {
                            ["Fifo"] = f_createFifo(),
                            ["BillboardGui"] = nil
                        }
                        local v_u_49 = nil
                        v_u_49 = v_u_43.data[p_u_48].Fifo.Emptied:connect(function() --[[ Line: 138 ]]
                            --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_43, (copy 3): p_u_48 ]]
                            v_u_49:disconnect()
                            v_u_43:Erase(p_u_48)
                        end)
                    end;
                    return v_u_43.data[p_u_48];
                end;
            end;
            v_u_43.GetData = function(_) --[[ Name: GetData ]] --[[ Line: 146 ]]
                --[[ Upvalues: (copy 1): v_u_43 ]]
                return v_u_43.data;
            end;
            return v_u_43;
        end)(),
        ["SanitizeChatLine"] = function(_, p50) --[[ Name: SanitizeChatLine ]] --[[ Line: 284 ]]
            if string.len(p50) > 124 then
                return string.sub(p50, 1, 127);
            else
                return p50;
            end;
        end,
        ["SetBillboardLODVeryFar"] = function(_, p51) --[[ Name: SetBillboardLODVeryFar ]] --[[ Line: 380 ]]
            p51.Enabled = false
        end,
        ["CreateBubbleText"] = function(_, p52) --[[ Name: CreateBubbleText ]] --[[ Line: 420 ]]
            --[[ Upvalues: (copy 1): l_SourceSans_0, (copy 2): l_Size24_0 ]]
            local l_TextLabel_0 = Instance.new("TextLabel")
            l_TextLabel_0.Name = "BubbleText"
            l_TextLabel_0.BackgroundTransparency = 1
            l_TextLabel_0.Position = UDim2.new(0, 15, 0, 0)
            l_TextLabel_0.Size = UDim2.new(1, -30, 1, 0)
            l_TextLabel_0.Font = l_SourceSans_0
            l_TextLabel_0.TextWrapped = true
            l_TextLabel_0.FontSize = l_Size24_0
            l_TextLabel_0.Text = p52
            l_TextLabel_0.AutoLocalize = false
            l_TextLabel_0.Visible = false
            return l_TextLabel_0;
        end,
        ["CreateSmallTalkBubble"] = function(_, _) --[[ Name: CreateSmallTalkBubble ]] --[[ Line: 436 ]]
            local l_ImageLabel_6 = Instance.new("ImageLabel")
            l_ImageLabel_6.Name = "SmallTalkBubble"
            l_ImageLabel_6.Size = UDim2.new(0, 0, 0, 0)
            l_ImageLabel_6.Position = UDim2.new(0, 0, 0, 0)
            l_ImageLabel_6.Visible = false
            return l_ImageLabel_6;
        end,
        ["DestroyBubble"] = function(_, p_u_53, p_u_54) --[[ Name: DestroyBubble ]] --[[ Line: 488 ]]
            if p_u_53 then
                if p_u_53:Empty() then
                    return;
                else
                    local l_RenderBubble_0 = p_u_53:Front().RenderBubble
                    if l_RenderBubble_0 then
                        spawn(function() --[[ Line: 498 ]]
                            --[[ Upvalues: (copy 1): p_u_53, (copy 2): p_u_54, (ref 3): l_RenderBubble_0 ]]
                            while p_u_53:Front().RenderBubble ~= p_u_54 do
                                wait()
                            end;
                            l_RenderBubble_0 = p_u_53:Front().RenderBubble
                            local v55 = l_RenderBubble_0:FindFirstChild("BubbleText")
                            local v56 = l_RenderBubble_0:FindFirstChild("ChatBubbleTail")
                            while l_RenderBubble_0 and l_RenderBubble_0.ImageTransparency < 1 do
                                local v57 = wait()
                                if l_RenderBubble_0 then
                                    local v58 = v57 * 1.5
                                    l_RenderBubble_0.ImageTransparency = l_RenderBubble_0.ImageTransparency + v58
                                    if v55 then
                                        v55.TextTransparency = v55.TextTransparency + v58
                                    end;
                                    if v56 then
                                        v56.ImageTransparency = v56.ImageTransparency + v58
                                    end;
                                end;
                            end;
                            if l_RenderBubble_0 then
                                l_RenderBubble_0:Destroy()
                                p_u_53:PopFront()
                            end;
                        end)
                    else
                        p_u_53:PopFront()
                    end;
                end;
            else
                return;
            end;
        end,
        ["ShowOwnFilteredMessage"] = function(_) --[[ Name: ShowOwnFilteredMessage ]] --[[ Line: 613 ]]
            return true;
        end
    }
    local function f_initChatBubbleType(p60, p61, _, p62, p63) --[[ Name: initChatBubbleType ]] --[[ Line: 273 ]]
        --[[ Upvalues: (copy 1): v_u_59, (copy 2): f_createChatBubbleMain, (copy 3): f_createScaledChatBubbleWithTail ]]
        v_u_59.ChatBubble[p60] = f_createChatBubbleMain(p61, p63)
        local l_ChatBubbleWithTail_0 = v_u_59.ChatBubbleWithTail
        local v64 = UDim2.new(0.5, -14, 1, p62 and -1 or 0)
        local v65 = UDim2.new(0, 30, 0, 14)
        local v66 = f_createChatBubbleMain(p61, p63)
        local l_ImageLabel_7 = Instance.new("ImageLabel")
        l_ImageLabel_7.Name = "ChatBubbleTail"
        l_ImageLabel_7.Image = "rbxasset://textures/ui/dialog_tail.png"
        l_ImageLabel_7.BackgroundTransparency = 1
        l_ImageLabel_7.BorderSizePixel = 0
        l_ImageLabel_7.Position = v64
        l_ImageLabel_7.Size = v65
        l_ImageLabel_7.Parent = v66
        l_ChatBubbleWithTail_0[p60] = v66
        v_u_59.ScalingChatBubbleWithTail[p60] = f_createScaledChatBubbleWithTail(p61, 0.5, UDim2.new(-0.5, 0, 0, p62 and -1 or 0), p63)
    end;
    f_initChatBubbleType(v_u_3.WHITE, "ui/dialog_white", "ui/chatBubble_white_notify_bkg", false, Rect.new(5, 5, 15, 15))
    f_initChatBubbleType(v_u_3.BLUE, "ui/dialog_blue", "ui/chatBubble_blue_notify_bkg", true, Rect.new(7, 7, 33, 33))
    f_initChatBubbleType(v_u_3.RED, "ui/dialog_red", "ui/chatBubble_red_notify_bkg", true, Rect.new(7, 7, 33, 33))
    f_initChatBubbleType(v_u_3.GREEN, "ui/dialog_green", "ui/chatBubble_green_notify_bkg", true, Rect.new(7, 7, 33, 33))
    local function f_createBillboardInstance(p67) --[[ Name: createBillboardInstance ]] --[[ Line: 292 ]]
        --[[ Upvalues: (copy 1): l_ScreenGui_0, (copy 2): v_u_59, (copy 3): v_u_3 ]]
        local l_BillboardGui_0 = Instance.new("BillboardGui")
        l_BillboardGui_0.Adornee = p67
        l_BillboardGui_0.Size = UDim2.new(0, 400, 0, 250)
        l_BillboardGui_0.StudsOffset = Vector3.new(0, 1.5, 2)
        l_BillboardGui_0.Parent = l_ScreenGui_0
        local l_Frame_1 = Instance.new("Frame")
        l_Frame_1.Name = "BillboardFrame"
        l_Frame_1.Size = UDim2.new(1, 0, 1, 0)
        l_Frame_1.Position = UDim2.new(0, 0, -0.5, 0)
        l_Frame_1.BackgroundTransparency = 1
        l_Frame_1.Parent = l_BillboardGui_0
        local v_u_68 = nil
        v_u_68 = l_Frame_1.ChildRemoved:connect(function() --[[ Line: 307 ]]
            --[[ Upvalues: (copy 1): l_Frame_1, (ref 2): v_u_68, (copy 3): l_BillboardGui_0 ]]
            if #l_Frame_1:GetChildren() <= 1 then
                v_u_68:disconnect()
                l_BillboardGui_0:Destroy()
            end;
        end)
        v_u_59:CreateSmallTalkBubble(v_u_3.WHITE).Parent = l_Frame_1
        return l_BillboardGui_0;
    end;
    v_u_59.CreateBillboardGuiHelper = function(_, p69, p70) --[[ Name: CreateBillboardGuiHelper ]] --[[ Line: 319 ]]
        --[[ Upvalues: (copy 1): v_u_59, (copy 2): f_createBillboardInstance ]]
        if p69 and not v_u_59.CharacterSortedMsg:Get(p69).BillboardGui then
            if not p70 and p69:IsA("BasePart") then
                v_u_59.CharacterSortedMsg:Get(p69).BillboardGui = f_createBillboardInstance(p69)
                return;
            end;
            if p69:IsA("Model") then
                local v71 = p69:FindFirstChild("Head")
                if v71 and v71:IsA("BasePart") then
                    v_u_59.CharacterSortedMsg:Get(p69).BillboardGui = f_createBillboardInstance(v71)
                end;
            end;
        end;
    end;
    local function _(p72) --[[ Name: distanceToBubbleOrigin ]] --[[ Line: 341 ]]
        return not p72 and 100000 or (p72.Position - game.Workspace.CurrentCamera.CoordinateFrame.p).magnitude;
    end;
    local function _(p73) --[[ Name: isPartOfLocalPlayer ]] --[[ Line: 347 ]]
        --[[ Upvalues: (ref 1): s_Players_0 ]]
        if p73 and s_Players_0.LocalPlayer.Character then
            return p73:IsDescendantOf(s_Players_0.LocalPlayer.Character);
        end;
    end;
    v_u_59.SetBillboardLODNear = function(_, p74) --[[ Name: SetBillboardLODNear ]] --[[ Line: 353 ]]
        --[[ Upvalues: (ref 1): s_Players_0 ]]
        local l_Adornee_0 = p74.Adornee
        local v75
        if l_Adornee_0 and s_Players_0.LocalPlayer.Character then
            v75 = l_Adornee_0:IsDescendantOf(s_Players_0.LocalPlayer.Character)
        else
            v75 = nil
        end;
        p74.Size = UDim2.new(0, 400, 0, 250)
        p74.StudsOffset = Vector3.new(0, v75 and 2 or 2.5, v75 and 2 or 0)
        p74.Enabled = true
        local v76 = p74.BillboardFrame:GetChildren()
        for v77 = 1, #v76 do
            v76[v77].Visible = true
        end;
        p74.BillboardFrame.SmallTalkBubble.Visible = false
    end;
    v_u_59.SetBillboardLODDistant = function(_, p78) --[[ Name: SetBillboardLODDistant ]] --[[ Line: 368 ]]
        --[[ Upvalues: (ref 1): s_Players_0 ]]
        local l_Adornee_1 = p78.Adornee
        local v79
        if l_Adornee_1 and s_Players_0.LocalPlayer.Character then
            v79 = l_Adornee_1:IsDescendantOf(s_Players_0.LocalPlayer.Character)
        else
            v79 = nil
        end;
        p78.Size = UDim2.new(4, 0, 3, 0)
        p78.StudsOffset = Vector3.new(0, 3, v79 and 2 or 0)
        p78.Enabled = true
        local v80 = p78.BillboardFrame:GetChildren()
        for v81 = 1, #v80 do
            v80[v81].Visible = false
        end;
        p78.BillboardFrame.SmallTalkBubble.Visible = true
    end;
    v_u_59.SetBillboardGuiLOD = function(_, p82, p83) --[[ Name: SetBillboardGuiLOD ]] --[[ Line: 384 ]]
        --[[ Upvalues: (copy 1): v_u_59 ]]
        if p83 then
            if p83:IsA("Model") then
                p83 = p83:FindFirstChild("Head") or p83.PrimaryPart
            end;
            if (not p83 and 100000 or (p83.Position - game.Workspace.CurrentCamera.CoordinateFrame.p).magnitude) < 100 then
                v_u_59:SetBillboardLODNear(p82)
            else
                v_u_59:SetBillboardLODVeryFar(p82)
            end;
        else
            return;
        end;
    end;
    v_u_59.UpdateAllLODs = function(_) --[[ Name: UpdateAllLODs ]] --[[ Line: 405 ]]
        --[[ Upvalues: (copy 1): v_u_59 ]]
        for v84, v85 in pairs(v_u_59.CharacterSortedMsg:GetData()) do
            local l_BillboardGui_1 = v85.BillboardGui
            if l_BillboardGui_1 then
                v_u_59:SetBillboardGuiLOD(l_BillboardGui_1, v84)
            end;
        end;
    end;
    v_u_59.HideAllLODs = function(_) --[[ Name: HideAllLODs ]] --[[ Line: 413 ]]
        --[[ Upvalues: (copy 1): v_u_59 ]]
        for _, v86 in pairs(v_u_59.CharacterSortedMsg:GetData()) do
            v_u_59:SetBillboardLODVeryFar(v86.BillboardGui)
        end;
    end;
    v_u_59.UpdateChatLinesForOrigin = function(_, p87, p88) --[[ Name: UpdateChatLinesForOrigin ]] --[[ Line: 458 ]]
        --[[ Upvalues: (copy 1): v_u_59 ]]
        local l_Fifo_0 = v_u_59.CharacterSortedMsg:Get(p87).Fifo
        local v89 = l_Fifo_0:Size()
        local v90 = l_Fifo_0:GetData()
        if #v90 > 1 then
            for v91 = #v90 - 1, 1, -1 do
                local l_RenderBubble_1 = v90[v91].RenderBubble
                if not l_RenderBubble_1 then
                    return;
                end;
                if v89 - v91 + 1 > 1 then
                    local v92 = l_RenderBubble_1:FindFirstChild("ChatBubbleTail")
                    if v92 then
                        v92:Destroy()
                    end;
                    local v93 = l_RenderBubble_1:FindFirstChild("BubbleText")
                    if v93 then
                        v93.TextTransparency = 0.5
                    end;
                end;
                l_RenderBubble_1.Position = UDim2.new(l_RenderBubble_1.Position.X.Scale, l_RenderBubble_1.Position.X.Offset, 1, p88 - l_RenderBubble_1.Size.Y.Offset - 14)
                p88 = p88 - l_RenderBubble_1.Size.Y.Offset - 14
            end;
        end;
    end;
    v_u_59.CreateChatLineRender = function(_, p94, p95, p96, p_u_97) --[[ Name: CreateChatLineRender ]] --[[ Line: 526 ]]
        --[[ Upvalues: (copy 1): v_u_59, (ref 2): s_TextService_0, (copy 3): l_SourceSans_0 ]]
        if p94 then
            if not v_u_59.CharacterSortedMsg:Get(p94).BillboardGui then
                v_u_59:CreateBillboardGuiHelper(p94, p96)
            end;
            local l_BillboardGui_2 = v_u_59.CharacterSortedMsg:Get(p94).BillboardGui
            if l_BillboardGui_2 then
                local v_u_98 = v_u_59.ChatBubbleWithTail[p95.BubbleColor]:Clone()
                v_u_98.Visible = false
                local v99 = v_u_59:CreateBubbleText(p95.Message)
                v99.Parent = v_u_98
                v_u_98.Parent = l_BillboardGui_2.BillboardFrame
                p95.RenderBubble = v_u_98
                local v100 = s_TextService_0:GetTextSize(v99.Text, 24, l_SourceSans_0, Vector2.new(400, 250))
                local v101 = math.max((v100.X + 30) / 400, 0.1)
                local v102 = v100.Y / 24 * 34
                v_u_98.Size = UDim2.new(v101, 0, 0, v102)
                v_u_98.Position = UDim2.new((1 - v101) / 2, 0, 1, -v102)
                v99.Visible = true
                v_u_59:SetBillboardGuiLOD(l_BillboardGui_2, p95.Origin)
                v_u_59:UpdateChatLinesForOrigin(p95.Origin, -v102)
                delay(p95.BubbleDieDelay, function() --[[ Line: 569 ]]
                    --[[ Upvalues: (ref 1): v_u_59, (copy 2): p_u_97, (copy 3): v_u_98 ]]
                    v_u_59:DestroyBubble(p_u_97, v_u_98)
                end)
            end;
        end;
    end;
    v_u_59.OnPlayerChatMessage = function(_, p103, p104, _) --[[ Name: OnPlayerChatMessage ]] --[[ Line: 575 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (copy 2): v_u_59, (copy 3): f_createChatLine, (copy 4): v_u_3 ]]
        local l_LocalPlayer_1 = s_Players_0.LocalPlayer
        local v105
        if l_LocalPlayer_1 == nil then
            v105 = false
        else
            v105 = p103 ~= l_LocalPlayer_1
        end;
        local v106 = f_createChatLine(v_u_59:SanitizeChatLine(p104), v_u_3.WHITE, not v105)
        if p103 then
            v106.User = p103.Name
            v106.Origin = p103.Character
        end;
        if p103 and v106.Origin then
            local l_Fifo_1 = v_u_59.CharacterSortedMsg:Get(v106.Origin).Fifo
            l_Fifo_1:PushBack(v106)
            v_u_59:CreateChatLineRender(p103.Character, v106, true, l_Fifo_1)
        end;
    end;
    v_u_59.OnGameChatMessage = function(_, p107, p108, p109) --[[ Name: OnGameChatMessage ]] --[[ Line: 591 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (copy 2): v_u_3, (copy 3): v_u_59, (copy 4): f_createChatLine ]]
        local l_LocalPlayer_2 = s_Players_0.LocalPlayer
        local v110
        if l_LocalPlayer_2 == nil then
            v110 = false
        else
            v110 = l_LocalPlayer_2.Character ~= p107
        end;
        local l_WHITE_0 = v_u_3.WHITE
        if p109 == Enum.ChatColor.Blue then
            l_WHITE_0 = v_u_3.BLUE
        elseif p109 == Enum.ChatColor.Green then
            l_WHITE_0 = v_u_3.GREEN
        elseif p109 == Enum.ChatColor.Red then
            l_WHITE_0 = v_u_3.RED
        end;
        local v111 = f_createChatLine(v_u_59:SanitizeChatLine(p108), l_WHITE_0, not v110)
        v111.Origin = p107
        v_u_59.CharacterSortedMsg:Get(v111.Origin).Fifo:PushBack(v111)
        v_u_59:CreateChatLineRender(p107, v111, false, v_u_59.CharacterSortedMsg:Get(v111.Origin).Fifo)
    end;
    local v_u_112 = true
    v_u_59.BubbleChatEnabled = function(_) --[[ Name: BubbleChatEnabled ]] --[[ Line: 609 ]]
        --[[ Upvalues: (ref 1): v_u_112 ]]
        return v_u_112;
    end;
    local function _(p113) --[[ Name: findPlayer ]] --[[ Line: 625 ]]
        --[[ Upvalues: (ref 1): s_Players_0 ]]
        for _, v114 in pairs(s_Players_0:GetPlayers()) do
            if v114.Name == p113 then
                return v114;
            end;
        end;
    end;
    local function _() --[[ Name: getAllowedMessageTypes ]] --[[ Line: 658 ]]
        return { "Message", "Whisper" };
    end;
    local function _(_) --[[ Name: checkAllowedMessageType ]] --[[ Line: 662 ]]
        return true;
    end;
    local v117 = {
        ["OnNewMessage"] = function(_, _, _) end,
        ["set_enabled"] = function(_, p115) --[[ Name: set_enabled ]] --[[ Line: 706 ]]
            --[[ Upvalues: (ref 1): v_u_112, (copy 2): v_u_59 ]]
            local v116 = v_u_112 ~= p115
            v_u_112 = p115
            if v116 and p115 ~= true then
                pcall(function() --[[ Line: 710 ]]
                    --[[ Upvalues: (ref 1): v_u_59 ]]
                    v_u_59:HideAllLODs()
                end)
            end;
        end
    }
    v117.OnMessageDoneFiltering = function(_, p118, _) --[[ Name: OnMessageDoneFiltering ]] --[[ Line: 682 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (ref 2): l_LocalPlayer_0, (copy 3): v_u_59 ]]
        local l_FromSpeaker_0 = p118.FromSpeaker
        for _, v120 in pairs(s_Players_0:GetPlayers()) do
            if v120.Name == l_FromSpeaker_0 then
                break;
            end;
        end;
        local v120 = nil
        -- ::l4:: (Possible bug with goto)
        if v120 then
            if p118.FromSpeaker ~= l_LocalPlayer_0.Name or v_u_59:ShowOwnFilteredMessage() then
                v_u_59:OnPlayerChatMessage(v120, p118.Message, nil)
            end;
        else
            return;
        end;
    end;
    v117.update = function(_) --[[ Name: update ]] --[[ Line: 695 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_112, (copy 3): v_u_59 ]]
        if v_u_1:do_disable_chat() then
            return;
        elseif v_u_112 == true then
            pcall(function() --[[ Line: 701 ]]
                --[[ Upvalues: (ref 1): v_u_59 ]]
                v_u_59:UpdateAllLODs()
            end)
        end;
    end;
    return v117;
end;
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 721 ]]
        --[[ Upvalues: (copy 1): f_SetupBubbleChat ]]
        return f_SetupBubbleChat();
    end
};
